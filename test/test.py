# test/test.py
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles

# Helpers ----------------------------------------------------------------------
def q4_4(value):
    """Convert a Python number to signed Q4.4 packed in 8-bit two's complement (0..255)."""
    raw = int(round(float(value) * 16.0))  # scale
    raw = max(-128, min(127, raw))         # clamp to signed 8-bit
    return raw & 0xFF                      # as unsigned 8-bit for assignment

def bit(val, i):
    """Extract bit i from an integer-like cocotb BinaryValue."""
    return (int(val) >> i) & 1

# Tests ------------------------------------------------------------------------
@cocotb.test()
async def lif_spikes_and_refractory_clears(dut):
    """Apply +2.0 Q4.4 input and expect a spike, refractory asserted, then cleared."""

    # 50 MHz -> 20ns period would also be fine; template uses arbitrary. We pick 10ns.
    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Init
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0

    # Reset (active-low), then release
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Drive +2.0 in Q4.4 (i.e., 32)
    dut.ui_in.value = q4_4(2.0)

    # Wait up to N cycles for a spike on uo_out[0]
    saw_spike = False
    for _ in range(256):
        await RisingEdge(dut.clk)
        if bit(dut.uo_out.value, 0):  # spike bit
            saw_spike = True
            break

    assert saw_spike, "Expected a spike with +2.0 input but didn't see one within 256 cycles."

    # On (or immediately after) the spike, refractory should be high
    # Advance one cycle to sample stable post-spike state.
    await RisingEdge(dut.clk)
    assert bit(dut.uo_out.value, 1) == 1, "Expected refractory to assert after spike."

    # Refractory should eventually clear as V is driven down below -THRESH
    cleared = False
    for _ in range(128):
        await RisingEdge(dut.clk)
        if bit(dut.uo_out.value, 1) == 0:
            cleared = True
            break
    assert cleared, "Refractory never cleared within 128 cycles."

@cocotb.test()
async def lif_no_spike_on_negative_current(dut):
    """Apply -1.0 Q4.4 and confirm no spike occurs in a short window."""

    cocotb.start_soon(Clock(dut.clk, 10, units="ns").start())

    # Init & reset
    dut.ena.value    = 1
    dut.ui_in.value  = 0
    dut.uio_in.value = 0
    dut.rst_n.value  = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    # Drive -1.0 in Q4.4 (i.e., -16)
    dut.ui_in.value = q4_4(-1.0)

    # Ensure no spike within a reasonable number of cycles
    for _ in range(128):
        await RisingEdge(dut.clk)
        assert bit(dut.uo_out.value, 0) == 0, "Unexpected spike with negative input current."
