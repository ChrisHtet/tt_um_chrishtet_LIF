import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

THRESH_Q44     = 0x40   #4.0 in Q4.4
REF_CYCLES     = 8
CLK_PERIOD_NS  = 10     #100 MHz
SETTLE_NS      = 1      #settle after each edge for GL sims

def spike_bit(dut) -> int:
    return int(dut.uo_out.value) & 0x1   # uo_out[0]

def vdbg_nibble(dut) -> int:
    return (int(dut.uo_out.value) >> 4) & 0xF  # uo_out[7:4]

async def tick_and_settle(dut, n=1):
    for _ in range(n):
        await RisingEdge(dut.clk)
        await Timer(SETTLE_NS, units="ns")

async def reset_and_start_clock(dut):
    dut.clk.value   = 0
    dut.rst_n.value = 0
    dut.ena.value   = 0
    dut.ui_in.value = 0
    dut.uio_in.value= 0
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
    await Timer(50, units="ns")   # settle
    dut.rst_n.value = 1
    await tick_and_settle(dut, 2)

async def wait_for_spike(dut, max_cycles: int) -> int:
    """Wait up to max_cycles after the *next* edge for a spike=1. Return cycle idx or -1."""
    for i in range(max_cycles):
        await RisingEdge(dut.clk)
        await Timer(SETTLE_NS, units="ns")
        if spike_bit(dut):
            return i
    return -1

@cocotb.test()
async def t0_quiet_when_disabled(dut):
    """While ena=0, all outputs must be 0."""
    await reset_and_start_clock(dut)
    for _ in range(5):
        await tick_and_settle(dut)
        assert dut.uo_out.value.is_resolvable
        assert int(dut.uo_out.value) == 0, "Outputs must be 0 when disabled"

@cocotb.test()
async def t1_spike_and_refractory(dut):
    """Enable with I=+4.0; expect an early spike, then REF_CYCLES of silence, then spike again."""
    await reset_and_start_clock(dut)

    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44

    # allows the first spike within the next 3 cycles
    first_idx = await wait_for_spike(dut, max_cycles=3)
    assert first_idx >= 0, "Expected an initial spike soon after enabling"

    # spike must be 1 cycle wide
    await tick_and_settle(dut)
    assert spike_bit(dut) == 0, "Spike must be one cycle wide"

    # refr: no spikes for REF_CYCLES cycles
    for i in range(REF_CYCLES):
        await tick_and_settle(dut)
        assert spike_bit(dut) == 0, f"No spike during refractory (cycle {i+1}/{REF_CYCLES})"

    #aft refr ends + I still high = another spike within a few cycles
    again_idx = await wait_for_spike(dut, max_cycles=3)
    assert again_idx >= 0, "Expected another spike after refractory ended"

@cocotb.test()
async def t2_subthreshold_no_spike(dut):
    """Small DC input (well below threshold steady state) should never spike."""
    await reset_and_start_clock(dut)
    dut.ena.value = 1

    # LSH=3 => V* = I * 2^LSH; choose I so V* < THRESH
    dut.ui_in.value = 0x07  # +0.4375 => V* ≈ 56 < 64
    for _ in range(120):
        await tick_and_settle(dut)
        assert spike_bit(dut) == 0, "No spikes expected for subthreshold input"

@cocotb.test()
async def t3_disable_midrun_gates_outputs(dut):
    """While running, drop ena->0; outputs must return to zero."""
    await reset_and_start_clock(dut)
    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44

    #let it spike once (tolerant window)
    _ = await wait_for_spike(dut, max_cycles=3)
    assert _ >= 0, "Expected an initial spike"

    #disable and ensure outputs go to 0 on next cycle
    dut.ena.value = 0
    await tick_and_settle(dut)
    assert int(dut.uo_out.value) == 0, "Outputs must be 0 when disabled"
