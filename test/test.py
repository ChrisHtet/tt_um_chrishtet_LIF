import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

THRESH_Q44   = 0x40   # 4.0 in Q4.4
REF_CYCLES   = 8
CLK_PERIOD_NS = 10    # 100 MHz

def spike(dut) -> int:
    return int(dut.uo_out.value) & 0x1

def v_dbg(dut) -> int:
    return (int(dut.uo_out.value) >> 4) & 0xF  # uo_out[7:4]

async def wait_cycles(dut, n: int):
    for _ in range(n):
        await RisingEdge(dut.clk)

async def reset_and_init(dut):
    dut.clk.value = 0
    dut.rst_n.value = 0
    dut.ena.value = 0
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, units="ns").start())
    await Timer(50, units="ns")
    dut.rst_n.value = 1
    await wait_cycles(dut, 2)

@cocotb.test()
async def t0_quiet_when_disabled(dut):
    await reset_and_init(dut)
    for _ in range(5):
        await RisingEdge(dut.clk)
        assert dut.uo_out.value.is_resolvable
        assert int(dut.uo_out.value) == 0

@cocotb.test()
async def t1_spike_and_refractory(dut):
    await reset_and_init(dut)
    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44
    await RisingEdge(dut.clk)
    assert spike(dut) == 1
    await RisingEdge(dut.clk)
    assert spike(dut) == 0
    for _ in range(REF_CYCLES):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0
        assert v_dbg(dut) == 0
    await RisingEdge(dut.clk)
    assert spike(dut) == 1

@cocotb.test()
async def t2_subthreshold_no_spike(dut):
    await reset_and_init(dut)
    dut.ena.value = 1
    dut.ui_in.value = 0x07  # +0.4375 => V* = 56 < 64
    for _ in range(80):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0
    assert v_dbg(dut) <= 0x3

@cocotb.test()
async def t3_negative_input_no_spike(dut):
    await reset_and_init(dut)
    dut.ena.value = 1
    dut.ui_in.value = 0xF0  # -1.0
    for _ in range(40):
        await RisingEdge(dut.clk)
        assert spike(dut) == 0

@cocotb.test()
async def t4_disable_midrun_gates_outputs(dut):
    await reset_and_init(dut)
    dut.ena.value = 1
    dut.ui_in.value = THRESH_Q44
    await RisingEdge(dut.clk)  # first spike
    assert spike(dut) == 1
    await RisingEdge(dut.clk)
    dut.ena.value = 0
    await RisingEdge(dut.clk)
    assert int(dut.uo_out.value) == 0
