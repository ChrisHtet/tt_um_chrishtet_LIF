# test/test.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

def q4_4(x):
    raw = int(round(float(x) * 16.0))
    raw = max(-128, min(127, raw))
    return raw & 0xFF

def bit(val, i): return (int(val) >> i) & 1

@cocotb.test()
async def lif_spikes_and_refractory_clears(dut):
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Hold reset (active-low), then release and KEEP released
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1    # <- release reset
    await ClockCycles(dut.clk, 2)

    # Drive +2.0 (Q4.4 = 32), wait for spike on uo_out[0]
    dut.ui_in.value = q4_4(2.0)
    for _ in range(256):
        await RisingEdge(dut.clk)
        if bit(dut.uo_out.value, 0):
            break
    else:
        assert False, "Expected a spike with +2.0 input"

    # Refractory should assert then clear
    await RisingEdge(dut.clk)
    assert bit(dut.uo_out.value, 1) == 1, "refractory should assert after spike"
    for _ in range(128):
        await RisingEdge(dut.clk)
        if bit(dut.uo_out.value, 1) == 0:
            break
    else:
        assert False, "refractory never cleared"
