module noc_interface (
        //inputs
        input wire clk,
        input wire rst_n,
        input wire internal_in,
        input wire external_in,

        //outputs
        output wire internal_out,
        output wire external_out,
);
reg [1:0] sync_internal, sync_external;
reg [7:0] op_code;
always @(posedge clk or negedge rst_n) begin 
    case (op_code)
        8'd2: //write
        8'd3: //read
        8'h20: //sector erase(4KiB)
        8'h52: //block erase(32KiB)
        8'hD8: //block erase(64KiB)
        8'h99: //reset device
        default: 
    endcase
    //count 16 bits
    //after 16 bits in <= out
    //Process OP code, decide action based on that
    //Generate acknowledgements at end of action
end
endmodule