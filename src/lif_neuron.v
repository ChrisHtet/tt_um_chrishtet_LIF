`timescale 1ns / 1ps

// Q4.4 fixed-point
    // Signed 8-bit: [-128, +127] where 1.0 = 16 (2^4)
    //Range: -8.0 to +7.9375

module lif_neuron #(
    parameter signed [7:0] THRESH_Q4_4 = 8'sd64,  // Threshold = 4.0
    parameter integer      LSH         = 3,       // leak shift= (V - V>>>LSH)
    parameter integer      REF_CYCLES  = 8        // refractory length in cycles
)(
    input  wire                 clk, rst_n, en,
    input  wire signed  [7:0]   I_q4_4,         // Voltage due to input current (Q4.4)
    output reg                  spike,          // 1-cycle spike
    output wire         [3:0]   V_dbg           // top bits of V for probing (unsigned view)
);

    // Membrane potential State Regs
    reg signed [7:0] V;    // membrane potential in Q4.4
    reg        [7:0] refr; // refractory counter (enough bits for REF_CYCLES)

    // Leak term: arithmetic shift preserves sign
    wire signed [7:0] leak = V >>> LSH; //leak = V / 2^LSH
    
    // Candidate next V with leak & input w/ 9 bits to catch overflow
    wire signed [8:0] V_next_wide = V + I_q4_4 - leak;      //Membrane potential(V) + Voltage due to input current(I_q4_4) - Leak(V>>LSH)
    // func to Saturate to signed 8-bit
    function signed [7:0] sat8;
        input signed [8:0] x;
        begin
            if (x > 9'sd127)      sat8 = 8'sd127;
            else if (x < -9'sd128) sat8 = -8'sd128;
            else                   sat8 = x[7:0];
        end
    endfunction
    wire signed [7:0] V_next = sat8(V_next_wide);    //call sat8 func

    wire will_spike = (refr == 0) && (V_next >= THRESH_Q4_4);    // Threshold cmp: spike when V >= THRESH

    assign V_dbg = V[7:4];    // Debug: expose MSBs of V (unsigned for easy LEDs)

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
