**Situation at the time.** There were no problems in simulation, but when run on the board, the results became very unstable.
Below are the actual logs, where you can see that the RMSE keeps changing between runs (0.0021-->0.438-->0.19... like this).
```bash
zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=0.036450327864808257  mae=0.044413571329261714  rmse=0.19091968956817487  relative_l2_percent=42.607667857855532

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=1.922004847537973  mae=0.27603421104830161  rmse=0.43840675733184802  relative_l2_percent=97.839513280905365

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=0.17515144233349755  mae=0.25971888029706136  rmse=0.418510982331971  relative_l2_percent=93.399360592141605

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...

zynqmp-common-20232:~/parabola-stp-fpga-endec-optimization-all-np64-rmws$ ./qif_snn_accuracy
mse=4.6093809508812285e-06  mae=0.0008461574139637662  rmse=0.002146946890559063  relative_l2_percent=0.479135495287...
```
Lowering the board clock to 200 MHz did not resolve the problem at all. 

Cause: The variables `candidate_network_base` and `chunk`, used to index the DDR memory named initial_nearest_candidates, were declared as signed int.
However, the constant offset `kInitialNearestChunkWinnerOffset` is unsigned int, and a bug occurred in the Vivado tool while trying to cast it to match the surrounding signed variables.
```cpp
int candidate_network_base;

for(int chunk = 0; chunk < kNearestChunkCount; chunk++) {
#pragma HLS PIPELINE II=1
    const initial_nearest_candidate_t initial_candidate =
        initial_nearest_candidates[candidate_network_base + kInitialNearestChunkWinnerOffset + chunk];
}

```

### After RTL synthesis

```verilog
wire signed [8:0] sext_ln59_1_fu_237_p1;
wire [8:0] add_ln59_fu_240_p2;
wire [63:0] zext_ln59_2_fu_246_p1;

assign sext_ln59_1_fu_237_p1 = $signed(sub_ln59_reg_513);
assign add_ln59_fu_240_p2 = ($signed(sext_ln59_1_fu_237_p1) + $signed(9'd384));
assign zext_ln59_2_fu_246_p1 = add_ln59_fu_240_p2;
assign add_ln59_1_fu_250_p2 = (zext_ln59_2_fu_246_p1 + initial_nearest_candidates);
```
`$signed(9'd384)` is interpreted as −128 when signed. However, zext_ln59_2_fu_246_p1 is an unsigned 9-bit signal.
It seems like it should be zero-extended automatically and work without any problems, but the Vivado tool misinterpreted this and generated a -128-byte offset into memory.
This ends up reading uninitialized DDR memory, and the behavior changes depending on what is stored there.

### RTL after the actual fix
After changing all indexing-related variables to unsigned, $signed(9'd384) is gone. This prevents an incorrect offset from being used.
```verilog
wire [10:0] sub_ln66_fu_224_p2;
wire signed [63:0] sext_ln66_1_fu_230_p1;

assign zext_ln66_cast_fu_196_p4 = {{{{3'd4}, {ap_sig_allocacmp_chunk_1}}}, {4'd0}};
assign zext_ln66_1_cast_fu_210_p4 = {{{{3'd4}, {ap_sig_allocacmp_chunk_1}}}, {2'd0}};
assign zext_ln66_fu_206_p1 = zext_ln66_cast_fu_196_p4;
assign zext_ln66_1_fu_220_p1 = zext_ln66_1_cast_fu_210_p4;
assign sub_ln66_fu_224_p2 = (zext_ln66_fu_206_p1 - zext_ln66_1_fu_220_p1);
assign sext_ln66_1_fu_230_p1 = $signed(sub_ln66_fu_224_p2);
assign add_ln66_fu_234_p2 = ($signed(sext_ln66_1_fu_230_p1) + $signed(initial_nearest_candidates));
```
