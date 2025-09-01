`timescale 1ns / 1ps
// Leaky Integrate-and-Fire with post-spike max, refractory down to -THRESH
// Fixed-point: Q4.4 on signed 8-bit: [-128, +127]; 1.0 = 16
// Range ≈ [-8.0, +7.9375]

module lif_core #(
    parameter signed [7:0] THRESH_Q4_4     = 8'sd64,   // +4.0
    parameter integer      LSH             = 3,        // leak shift: leak = V >>> LSH
    parameter signed [7:0] V_MAX_Q4_4      = 8'sd127,  // set V to max on spike
    parameter signed [7:0] NEG_DRIVE_Q4_4  = 8'sd16    // extra negative drive during refractory (1.0)
)(
    input  wire                 clk, rst_n, en,
    input  wire signed  [7:0]   I_q4_4,     // input increment (Q4.4)
    output reg                  spike,      // 1-cycle pulse on spike
    output reg                  refractory, // high while in refractory
    output reg  signed  [7:0]   V_q4_4,     // membrane potential (Q4.4)
    output wire         [3:0]   V_dbg       // MSBs for quick probing
);
    // ---- helpers ----
    wire signed [7:0] leak = V_q4_4 >>> LSH;

    // normal path (integrate + leak)
    wire signed [8:0] V_norm_wide = V_q4_4 + I_q4_4 - leak;

    // refractory path (ignore input, push down)
    wire signed [8:0] V_refr_wide = V_q4_4 - leak - NEG_DRIVE_Q4_4;

    // saturate to signed 8-bit
    function signed [7:0] sat8;
        input signed [8:0] x;
        begin
            if      (x >  9'sd127)  sat8 = 8'sd127;
            else if (x < -9'sd128)  sat8 = -8'sd128;
            else                    sat8 = x[7:0];
        end
    endfunction

    wire signed [7:0] V_norm_next  = sat8(V_norm_wide);
    wire signed [7:0] V_refr_next  = sat8(V_refr_wide);

    // Spike detection only when not refractory
    wire will_spike = (!refractory) && (V_norm_next >= THRESH_Q4_4);

    assign V_dbg = V_q4_4[7:4];

    // ---- sequential ----
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            V_q4_4     <= 8'sd0;
            spike      <= 1'b0;
            refractory <= 1'b0;
        end else begin
            spike <= 1'b0; // default

            if (en) begin
                if (refractory) begin
                    V_q4_4 <= V_refr_next;
                    if (V_refr_next <= -THRESH_Q4_4)// Exit refr IF V <= -THRESH
                        refractory <= 1'b0;
                end else if (will_spike) begin  // Spike and set V to max, then enter refractory
                    spike      <= 1'b1;
                    V_q4_4     <= V_MAX_Q4_4;
                    refractory <= 1'b1;
                end else begin                  // Normal integrate+leak
                    V_q4_4     <= V_norm_next;
                    refractory <= 1'b0;
                end
            end
        end
    end

endmodule
