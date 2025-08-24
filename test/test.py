import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

@cocotb.test()
async def lif_smoke(dut):
    # start 100 MHz clock
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # reset low, disabled
    dut.rst_n.value = 0
    dut.ena.value   = 0
    dut.ui_in.value = 0
    dut.uio_in.value= 0
    await Timer(50, units="ns")
    dut.rst_n.value = 1

    # while disabled, outputs must be zero
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert int(dut.uo_out.value) == 0

    # enable and give a constant current (+4.0 in Q4.4)
    dut.ena.value = 1
    dut.ui_in.value = 0x40
    for _ in range(50):
        await RisingEdge(dut.clk)

    # basic sanity: signals are driven (no X/Z)
    assert dut.uo_out.value.is_resolvable
'''
# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_project(dut):
    dut._log.info("Start")

    # Set the clock period to 10 us (100 KHz)
    clock = Clock(dut.clk, 10, units="us")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 10)
    dut.rst_n.value = 1

    dut._log.info("Test project behavior")

    # Set the input values you want to test
    dut.ui_in.value = 20
    dut.uio_in.value = 30

    # Wait for one clock cycle to see the output values
    await ClockCycles(dut.clk, 1)

    # The following assersion is just an example of how to check the output values.
    # Change it to match the actual expected output of your module:
    assert dut.uo_out.value == 50

    # Keep testing the module by changing the input values, waiting for
    # one or more clock cycles, and asserting the expected output values.
'''
