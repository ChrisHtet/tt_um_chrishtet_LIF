# test/test.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

# Match your RTL params
THRESH_Q44   = 0x40   # 4.0 in Q4.4
REF_CYCLES   = 8
CLK_PERIOD_NS = 10    # 100 MHz

def spike(dut) -> int:
    return int(dut.uo_out.value) & 0x1

def v_dbg(dut) -> int:
    # top nibble of V (uo_out[7:4])
    return (int(dut.uo_out.value) >> 4) & 0xF

async def wait_cycles(dut, n: int):
    for _ in range(n):
        await RisingEdge(dut.clk)

async def reset_and_init(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    # start clock
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
    await Timer(50, units="ns")   # let tb settle a bit
    dut.rst_n.value = 1
    await wait_cycles(dut, 2)

@cocotb.test()
async def t0_quiet_when_disabled(dut):
    """While ena=0, all outputs must be 0."""
    await reset_and_init(dut)
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert dut.uo_out.value.is_resolvable
        assert int(dut.uo_out.value) == 0, "Outputs must be zero while disabled"

@cocotb.test()
async def t1_spike_and_refractory(dut):
    """Drive I=+4.0 (0x40). Expect an immediate spike, then REF_CYCLES of silence, then spike again."""
    await reset_and_init(dut)

    # enable and apply +4.0 (hits threshold exactly from V=0)
    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44

    # First cycle after enabling -> should spike for 1 cycle
    await RisingEdge(dut.clk)
    assert spike(dut) == 1, "Should spike when V_next >= threshold"
    await RisingEdge(dut.clk)
    assert spike(dut) == 0, "Spike must be one-cycle wide"

    # During refractory: no spike and V_dbg stays 0
    for i in range(REF_CYCLES):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0, f"No spike during refractory (cycle {i+1}/{REF_CYCLES})"
        assert v_dbg(dut) == 0, "V must hold at 0 during refractory"

    # Next cycle: refractory ended; with I still high we should spike again
    await RisingEdge(dut.clk)
    assert spike(dut) == 1, "Should spike again right after refractory ends"

@cocotb.test()
async def t2_subthreshold_no_spike(dut):
    """Apply small DC input (< threshold/2^LSH). Expect no spikes; V_dbg should settle below 0x4."""
    await reset_and_init(dut)
    dut.ena.value = 1

    # Choose I so steady-state V* = I * 2^LSH < THRESH (LSH=3 -> V* = 8*I).
    # I=0x07 (0.4375) -> V* = 56 < 64, so no spike should ever happen.
    dut.ui_in.value = 0x07
    for _ in range(80):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0, "No spikes expected for subthreshold input"

    # After settling, top nibble should be <= 0x3 (below 0x40)
    assert v_dbg(dut) <= 0x3, f"V_dbg too high: {v_dbg(dut):x}"

@cocotb.test()
async def t3_negative_input_no_spike(dut):
    """Negative input should not produce spikes."""
    await reset_and_init(dut)
    dut.ena.value = 1

    # -1.0 in Q4.4 = -16 = 0xF0
    dut.ui_in.value = 0xF0
    for _ in range(40):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0, "No spikes expected for negative input"

@cocotb.test()
async def t4_disable_midrun_gates_outputs(dut):
    """While running, drop ena->0 and check outputs go to zero."""
    await reset_and_init(dut)
    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44

    # Let it spike once
    await RisingEdge(dut.clk)
    assert spike(dut) == 1
    await RisingEdge(dut.clk)

    # Disable and ensure outputs are zeroed (gated by ena)
    dut.ena.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.uo_out.value) == 0, "Outputs must be 0 when disabled"

'''import cocotb
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
