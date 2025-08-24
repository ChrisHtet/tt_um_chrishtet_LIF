/*
 * Copyright (c) 2025 Chris Htet
 * SPDX-License-Identifier: Apache-2.0
 */

`default_nettype none

module tt_um_chrishtet_LIF (
`ifdef GL_TEST
    input wire VPWR, input wire VGND,
`endif
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
    assign uio_out = 8'b0;
    assign uio_oe  = 8'b0;
    assign uo_out[0]   = ena ? spike : 1'b0;      //not used
    assign uo_out[7:4] = ena ? V_dbg  : 4'b0000; //MSBs of membrane V
    assign uo_out[3:1] = 3'b000;

  wire signed [7:0] I_q4_4 =ui_in;
  wire spike;
  wire [3:0] V_dbg;
    
    lif_neuron #(
        .THRESH_Q4_4(8'sd64), // 4.0
        .LSH(3),
        .REF_CYCLES(8)
    ) lif (
        .clk   (clk),
        .rst_n (rst_n),
        .en    (ena),  
        .I_q4_4(I_q4_4),
        .spike (spike),
        .V_dbg (V_dbg)
    );
// List all unused inputs to prevent warnings
//i.e: wire _unused = &{ena, clk, rst_n, 1'b0};
    wire _unused = &{uio_in, 1'b0};
endmodule
