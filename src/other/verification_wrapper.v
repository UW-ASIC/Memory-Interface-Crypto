module verification_wrapper #(
  parameter integer length = 16
)(
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,   // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);
	reg pos[7:0] = 8'b0;

	wire output_wire[length - 1 : 0];
	wire io_ena_wire[length - 1 : 0];
	wire io_out_wire[length - 1 : 0];

	reg out_out_buf[7:0];
	reg io_ena_buf[7:0];
	reg io_out_buf[7:0];

	assign uo_out = out_out_buf;
	assign uio_oe = io_ena_buf;
	assign uio_out = io_out_buf;

	reg in_in_buf[length - 1 : 0];
	reg io_in_buf[length - 1 : 0];

	reg slow_clk;
	always @(posedge clk or negedge rst_n) begin
		if(!rst_n) begin
			uo_out = 8'b0;
			uio_in = 8'b0;
			pos <= 0;
			out_out_buf <= 0;
			in_in_buf <= 0;
			io_ena_buf <= 0;
			io_out_buf <= 0;
			inout_buf_module_side <= 0;
			io_ena_buf <= 0;
			pos = 0;
		end 
		else begin
			if(pos + 8 < length) begin
				out_out_buf <= output_wire[pos + 7 : pos];

				in_in_buf[pos + 7 : pos] <= uo_in;
				io_in_buf[pos + 7 : pos] <= (uio_in & ~uio_oe);

				io_out_buf <= (io_out_wire[pos + 7 : pos] & uio_oe) | (uio_in & ~uio_oe);
				io_ena_buf <= io_ena_wire[pos + 7 : pos];

				pos <= pos + 8;
			end
			else begin
				slow_clk <= ~slow_clk;
				pos = 0;
			end
		end
	end

	// my_core core (
	// 	.clk    (slow_clk),
	// 	.rst_n  (rst_n),
	// 	.ce     (core_ce),   
	// 	.in_bus (active_in),
	// 	.obs_bus(core_obs)
	// );
endmodule
