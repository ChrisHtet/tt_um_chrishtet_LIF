`timescale 1ns / 1ps

// Q4.4 fixed-point: Signed 8-bit [-8.0, +7.9375] where 1.0 = 16 (2^4)

module lif_neuron #(
    parameter signed [7:0] THRESH_Q4_4 = 8'sd64,  // Threshold = 4.0
    parameter integer      LSH         = 3,       // Leak shift (V - V>>LSH)
    parameter integer      REF_CYCLES  = 8        // Refractory length in cycles
)(
    input  wire                 clk, rst_n, en,
    input  wire signed  [7:0]   I_q4_4,         // Voltage due to input current (Q4.4)
    output reg                  spike,          // 1-cycle spike
    output wire         [3:0]   V_dbg           // Top bits of V for probing (unsigned view)
);

    // Membrane potential State Regs
    reg signed [7:0] V;    // Membrane potential in Q4.4
    reg        [7:0] refr; // Refractory counter (enough bits for REF_CYCLES)

    // Leak term: arithmetic shift preserves sign
    wire signed [7:0] leak = V >> LSH;  // Changed to >> for arithmetic shift
    
    // Sign-extend operands to 10-bit to prevent wrap-around in sum
    wire signed [9:0] V_wide = V;
    wire signed [9:0] I_wide = I_q4_4;
    wire signed [9:0] leak_wide = leak;
    
    // Candidate next V with leak & input (10-bit to catch full overflow range)
    wire signed [9:0] V_next_wide = V_wide + I_wide - leak_wide;
    
    // Saturate to signed 8-bit using ternary (better for synthesis than function)
    wire signed [7:0] V_next = (V_next_wide > 10'sd127) ? 8'sd127 :
                               (V_next_wide < -10'sd128) ? -8'sd128 :
                               V_next_wide[7:0];

    wire will_spike = (refr == 0) && (V_next >= THRESH_Q4_4);  // Threshold cmp

    assign V_dbg = V[7:4];  // Debug: expose MSBs of V (unsigned for easy LEDs)

    // Sequential logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            V     <= 8'sd0;
            spike <= 1'b0;
            refr  <= 8'd0;
        end else begin
            spike <= 1'b0; // default
            if (en) begin
                if (refr != 0) begin            // In refractory: hold V at 0 and count down
                    V    <= 8'sd0;
                    refr <= refr - 1'b1;
                end else if (will_spike) begin  // Emit spike and enter refractory
                    spike <= 1'b1;
                    V     <= 8'sd0;
                    refr  <= (REF_CYCLES != 0) ? REF_CYCLES[7:0] : 8'd0;
                end else begin
                    V    <= V_next;             // Normal integrate+leak
                    refr <= 8'd0;
                end
            end
        end
    end

endmodule
