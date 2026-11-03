// Generated from the saved DEM. Do not edit this generated file.
module local_predecoder (
 input wire clk, input wire rst,
 input wire in_valid, output wire in_ready,
 input wire [23:0] syndrome,
 output reg out_valid, input wire out_ready,
 output reg [23:0] residual,
 output reg [0:0] frame
);
wire [53:0] active;
wire [53:0] chosen;
wire [23:0] next_residual;
wire [0:0] next_frame;
assign in_ready = !out_valid || out_ready;

assign active[0] = syndrome[0] & syndrome[1];
assign chosen[0] = active[0] & ~(active[1] | active[2] | active[3] | active[4]);
assign active[1] = syndrome[0] & syndrome[8];
assign chosen[1] = active[1] & ~(active[0] | active[4] | active[7] | active[14] | active[25]);
assign active[2] = syndrome[1] & syndrome[2];
assign chosen[2] = active[2] & ~(active[0] | active[3] | active[4] | active[5] | active[6] | active[7] | active[8]);
assign active[3] = syndrome[1] & syndrome[5];
assign chosen[3] = active[3] & ~(active[0] | active[2] | active[4] | active[6] | active[9] | active[14] | active[15] | active[16] | active[17]);
assign active[4] = syndrome[1] & syndrome[8];
assign chosen[4] = active[4] & ~(active[0] | active[1] | active[2] | active[3] | active[7] | active[14] | active[25]);
assign active[5] = syndrome[2] & syndrome[3];
assign chosen[5] = active[5] & ~(active[2] | active[6] | active[7] | active[8] | active[9] | active[10] | active[11]);
assign active[6] = syndrome[2] & syndrome[5];
assign chosen[6] = active[6] & ~(active[2] | active[3] | active[5] | active[7] | active[8] | active[9] | active[14] | active[15] | active[16] | active[17]);
assign active[7] = syndrome[2] & syndrome[8];
assign chosen[7] = active[7] & ~(active[1] | active[2] | active[4] | active[5] | active[6] | active[8] | active[14] | active[25]);
assign active[8] = syndrome[2] & syndrome[10];
assign chosen[8] = active[8] & ~(active[2] | active[5] | active[6] | active[7] | active[11] | active[15] | active[21] | active[30] | active[31] | active[32]);
assign active[9] = syndrome[3] & syndrome[5];
assign chosen[9] = active[9] & ~(active[3] | active[5] | active[6] | active[10] | active[11] | active[14] | active[15] | active[16] | active[17]);
assign active[10] = syndrome[3] & syndrome[7];
assign chosen[10] = active[10] & ~(active[5] | active[9] | active[11] | active[21] | active[22] | active[23] | active[24]);
assign active[11] = syndrome[3] & syndrome[10];
assign chosen[11] = active[11] & ~(active[5] | active[8] | active[9] | active[10] | active[15] | active[21] | active[30] | active[31] | active[32]);
assign active[12] = syndrome[4] & syndrome[6];
assign chosen[12] = active[12] & ~(active[13] | active[18] | active[19] | active[20]);
assign active[13] = syndrome[4] & syndrome[12];
assign chosen[13] = active[13] & ~(active[12] | active[19] | active[27] | active[36]);
assign active[14] = syndrome[5] & syndrome[8];
assign chosen[14] = active[14] & ~(active[1] | active[3] | active[4] | active[6] | active[7] | active[9] | active[15] | active[16] | active[17] | active[25]);
assign active[15] = syndrome[5] & syndrome[10];
assign chosen[15] = active[15] & ~(active[3] | active[6] | active[8] | active[9] | active[11] | active[14] | active[16] | active[17] | active[21] | active[30] | active[31] | active[32]);
assign active[16] = syndrome[5] & syndrome[13];
assign chosen[16] = active[16] & ~(active[3] | active[6] | active[9] | active[14] | active[15] | active[17] | active[22] | active[30] | active[37] | active[38] | active[39] | active[40]);
assign active[17] = syndrome[5] & syndrome[16];
assign chosen[17] = active[17] & ~(active[3] | active[6] | active[9] | active[14] | active[15] | active[16] | active[25] | active[31] | active[37] | active[46]);
assign active[18] = syndrome[6] & syndrome[9];
assign chosen[18] = active[18] & ~(active[12] | active[19] | active[20] | active[26] | active[27] | active[28] | active[29]);
assign active[19] = syndrome[6] & syndrome[12];
assign chosen[19] = active[19] & ~(active[12] | active[13] | active[18] | active[20] | active[27] | active[36]);
assign active[20] = syndrome[6] & syndrome[14];
assign chosen[20] = active[20] & ~(active[12] | active[18] | active[19] | active[28] | active[33] | active[36] | active[41]);
assign active[21] = syndrome[7] & syndrome[10];
assign chosen[21] = active[21] & ~(active[8] | active[10] | active[11] | active[15] | active[22] | active[23] | active[24] | active[30] | active[31] | active[32]);
assign active[22] = syndrome[7] & syndrome[13];
assign chosen[22] = active[22] & ~(active[10] | active[16] | active[21] | active[23] | active[24] | active[30] | active[37] | active[38] | active[39] | active[40]);
assign active[23] = syndrome[7] & syndrome[15];
assign chosen[23] = active[23] & ~(active[10] | active[21] | active[22] | active[24] | active[42] | active[43] | active[44] | active[45]);
assign active[24] = syndrome[7] & syndrome[18];
assign chosen[24] = active[24] & ~(active[10] | active[21] | active[22] | active[23] | active[32] | active[38] | active[42] | active[48] | active[49] | active[50]);
assign active[25] = syndrome[8] & syndrome[16];
assign chosen[25] = active[25] & ~(active[1] | active[4] | active[7] | active[14] | active[17] | active[31] | active[37] | active[46]);
assign active[26] = syndrome[9] & syndrome[11];
assign chosen[26] = active[26] & ~(active[18] | active[27] | active[28] | active[29] | active[33] | active[34] | active[35]);
assign active[27] = syndrome[9] & syndrome[12];
assign chosen[27] = active[27] & ~(active[13] | active[18] | active[19] | active[26] | active[28] | active[29] | active[36]);
assign active[28] = syndrome[9] & syndrome[14];
assign chosen[28] = active[28] & ~(active[18] | active[20] | active[26] | active[27] | active[29] | active[33] | active[36] | active[41]);
assign active[29] = syndrome[9] & syndrome[17];
assign chosen[29] = active[29] & ~(active[18] | active[26] | active[27] | active[28] | active[34] | active[41] | active[47]);
assign active[30] = syndrome[10] & syndrome[13];
assign chosen[30] = active[30] & ~(active[8] | active[11] | active[15] | active[16] | active[21] | active[22] | active[31] | active[32] | active[37] | active[38] | active[39] | active[40]);
assign active[31] = syndrome[10] & syndrome[16];
assign chosen[31] = active[31] & ~(active[8] | active[11] | active[15] | active[17] | active[21] | active[25] | active[30] | active[32] | active[37] | active[46]);
assign active[32] = syndrome[10] & syndrome[18];
assign chosen[32] = active[32] & ~(active[8] | active[11] | active[15] | active[21] | active[24] | active[30] | active[31] | active[38] | active[42] | active[48] | active[49] | active[50]);
assign active[33] = syndrome[11] & syndrome[14];
assign chosen[33] = active[33] & ~(active[20] | active[26] | active[28] | active[34] | active[35] | active[36] | active[41]);
assign active[34] = syndrome[11] & syndrome[17];
assign chosen[34] = active[34] & ~(active[26] | active[29] | active[33] | active[35] | active[41] | active[47]);
assign active[35] = syndrome[11] & syndrome[19];
assign chosen[35] = active[35] & ~(active[26] | active[33] | active[34] | active[47]);
assign active[36] = syndrome[12] & syndrome[14];
assign chosen[36] = active[36] & ~(active[13] | active[19] | active[20] | active[27] | active[28] | active[33] | active[41]);
assign active[37] = syndrome[13] & syndrome[16];
assign chosen[37] = active[37] & ~(active[16] | active[17] | active[22] | active[25] | active[30] | active[31] | active[38] | active[39] | active[40] | active[46]);
assign active[38] = syndrome[13] & syndrome[18];
assign chosen[38] = active[38] & ~(active[16] | active[22] | active[24] | active[30] | active[32] | active[37] | active[39] | active[40] | active[42] | active[48] | active[49] | active[50]);
assign active[39] = syndrome[13] & syndrome[20];
assign chosen[39] = active[39] & ~(active[16] | active[22] | active[30] | active[37] | active[38] | active[40] | active[46] | active[48] | active[51]);
assign active[40] = syndrome[13] & syndrome[21];
assign chosen[40] = active[40] & ~(active[16] | active[22] | active[30] | active[37] | active[38] | active[39] | active[43] | active[49] | active[51] | active[52]);
assign active[41] = syndrome[14] & syndrome[17];
assign chosen[41] = active[41] & ~(active[20] | active[28] | active[29] | active[33] | active[34] | active[36] | active[47]);
assign active[42] = syndrome[15] & syndrome[18];
assign chosen[42] = active[42] & ~(active[23] | active[24] | active[32] | active[38] | active[43] | active[44] | active[45] | active[48] | active[49] | active[50]);
assign active[43] = syndrome[15] & syndrome[21];
assign chosen[43] = active[43] & ~(active[23] | active[40] | active[42] | active[44] | active[45] | active[49] | active[51] | active[52]);
assign active[44] = syndrome[15] & syndrome[22];
assign chosen[44] = active[44] & ~(active[23] | active[42] | active[43] | active[45] | active[50] | active[52] | active[53]);
assign active[45] = syndrome[15] & syndrome[23];
assign chosen[45] = active[45] & ~(active[23] | active[42] | active[43] | active[44] | active[53]);
assign active[46] = syndrome[16] & syndrome[20];
assign chosen[46] = active[46] & ~(active[17] | active[25] | active[31] | active[37] | active[39] | active[48] | active[51]);
assign active[47] = syndrome[17] & syndrome[19];
assign chosen[47] = active[47] & ~(active[29] | active[34] | active[35] | active[41]);
assign active[48] = syndrome[18] & syndrome[20];
assign chosen[48] = active[48] & ~(active[24] | active[32] | active[38] | active[39] | active[42] | active[46] | active[49] | active[50] | active[51]);
assign active[49] = syndrome[18] & syndrome[21];
assign chosen[49] = active[49] & ~(active[24] | active[32] | active[38] | active[40] | active[42] | active[43] | active[48] | active[50] | active[51] | active[52]);
assign active[50] = syndrome[18] & syndrome[22];
assign chosen[50] = active[50] & ~(active[24] | active[32] | active[38] | active[42] | active[44] | active[48] | active[49] | active[52] | active[53]);
assign active[51] = syndrome[20] & syndrome[21];
assign chosen[51] = active[51] & ~(active[39] | active[40] | active[43] | active[46] | active[48] | active[49] | active[52]);
assign active[52] = syndrome[21] & syndrome[22];
assign chosen[52] = active[52] & ~(active[40] | active[43] | active[44] | active[49] | active[50] | active[51] | active[53]);
assign active[53] = syndrome[22] & syndrome[23];
assign chosen[53] = active[53] & ~(active[44] | active[45] | active[50] | active[52]);
assign next_residual[0] = syndrome[0] ^ (chosen[0] ^ chosen[1]);
assign next_residual[1] = syndrome[1] ^ (chosen[0] ^ chosen[2] ^ chosen[3] ^ chosen[4]);
assign next_residual[2] = syndrome[2] ^ (chosen[2] ^ chosen[5] ^ chosen[6] ^ chosen[7] ^ chosen[8]);
assign next_residual[3] = syndrome[3] ^ (chosen[5] ^ chosen[9] ^ chosen[10] ^ chosen[11]);
assign next_residual[4] = syndrome[4] ^ (chosen[12] ^ chosen[13]);
assign next_residual[5] = syndrome[5] ^ (chosen[3] ^ chosen[6] ^ chosen[9] ^ chosen[14] ^ chosen[15] ^ chosen[16] ^ chosen[17]);
assign next_residual[6] = syndrome[6] ^ (chosen[12] ^ chosen[18] ^ chosen[19] ^ chosen[20]);
assign next_residual[7] = syndrome[7] ^ (chosen[10] ^ chosen[21] ^ chosen[22] ^ chosen[23] ^ chosen[24]);
assign next_residual[8] = syndrome[8] ^ (chosen[1] ^ chosen[4] ^ chosen[7] ^ chosen[14] ^ chosen[25]);
assign next_residual[9] = syndrome[9] ^ (chosen[18] ^ chosen[26] ^ chosen[27] ^ chosen[28] ^ chosen[29]);
assign next_residual[10] = syndrome[10] ^ (chosen[8] ^ chosen[11] ^ chosen[15] ^ chosen[21] ^ chosen[30] ^ chosen[31] ^ chosen[32]);
assign next_residual[11] = syndrome[11] ^ (chosen[26] ^ chosen[33] ^ chosen[34] ^ chosen[35]);
assign next_residual[12] = syndrome[12] ^ (chosen[13] ^ chosen[19] ^ chosen[27] ^ chosen[36]);
assign next_residual[13] = syndrome[13] ^ (chosen[16] ^ chosen[22] ^ chosen[30] ^ chosen[37] ^ chosen[38] ^ chosen[39] ^ chosen[40]);
assign next_residual[14] = syndrome[14] ^ (chosen[20] ^ chosen[28] ^ chosen[33] ^ chosen[36] ^ chosen[41]);
assign next_residual[15] = syndrome[15] ^ (chosen[23] ^ chosen[42] ^ chosen[43] ^ chosen[44] ^ chosen[45]);
assign next_residual[16] = syndrome[16] ^ (chosen[17] ^ chosen[25] ^ chosen[31] ^ chosen[37] ^ chosen[46]);
assign next_residual[17] = syndrome[17] ^ (chosen[29] ^ chosen[34] ^ chosen[41] ^ chosen[47]);
assign next_residual[18] = syndrome[18] ^ (chosen[24] ^ chosen[32] ^ chosen[38] ^ chosen[42] ^ chosen[48] ^ chosen[49] ^ chosen[50]);
assign next_residual[19] = syndrome[19] ^ (chosen[35] ^ chosen[47]);
assign next_residual[20] = syndrome[20] ^ (chosen[39] ^ chosen[46] ^ chosen[48] ^ chosen[51]);
assign next_residual[21] = syndrome[21] ^ (chosen[40] ^ chosen[43] ^ chosen[49] ^ chosen[51] ^ chosen[52]);
assign next_residual[22] = syndrome[22] ^ (chosen[44] ^ chosen[50] ^ chosen[52] ^ chosen[53]);
assign next_residual[23] = syndrome[23] ^ (chosen[45] ^ chosen[53]);
assign next_frame[0] = 1'b0;
always @(posedge clk) begin
 if (rst) begin
  out_valid <= 1'b0; residual <= 0; frame <= 0;
 end else if (in_ready) begin
  out_valid <= in_valid;
  if (in_valid) begin residual <= next_residual; frame <= next_frame; end
 end
end
endmodule
