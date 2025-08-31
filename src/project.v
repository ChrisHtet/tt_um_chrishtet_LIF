/*
 * Copyright (c) 2024 Your Name
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_chrishtet_LIF (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

  // All output pins must be assigned. If not used, assign to 0.

    wire signed [7:0] I_q4_4 = ui_in;   // use all 8 ui_in bits as signed Q4.4 input
    wire              lif_en = ena;     // TT 'ena' is always 1 when powered

    // Wires from core
    wire        spike;
    wire        refractory;
    wire signed [7:0] V_q4_4;
    wire [3:0]  V_dbg;

    // Instantiate the neuron core
    lif_core #(
        .THRESH_Q4_4(8'sd64),       // +4.0 (Q4.4)
        .LSH(3),
        .V_MAX_Q4_4(8'sd127),
        .NEG_DRIVE_Q4_4(8'sd16)
    ) u_core (
        .clk(clk),
        .rst_n(rst_n),
        .en(lif_en),
        .I_q4_4(I_q4_4),
        .spike(spike),
        .refractory(refractory),
        .V_q4_4(V_q4_4),
        .V_dbg(V_dbg)
    );

    // Driving all required outputs (no undriven pins!)
    assign uo_out[0]   = spike;
    assign uo_out[1]   = refractory;
    assign uo_out[5:2] = V_dbg;         // 4-bit scope view of V[7:4]
    assign uo_out[7:6] = 2'b00;
    // Bidir IOs not used
  assign uio_out = 0;
  assign uio_oe  = 0;

  // List all unused inputs to prevent warnings
  wire _unused = &{uio_in, 1'b0};

endmodule
