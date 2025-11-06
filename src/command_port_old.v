/*

Help facilitate communication between our module and other modules on the bus. 

Checks whenever new data is available and send acknowledgements according

The command given to us will be something in this format:

dest id, opcode, address/data

We read all this from the bus and know that the message is meant for us and acknowledge that
we have received this command. We can then pass the command to the Transaction FSM

*/

module command_port (
    //inputs
    input wire clk,
    input wire rst_n,
    input wire sp_done,
    input wire sp_we,
    input wire sp_qe,             // Quad enable. QE = 0 means flash operates in standard SPI mode (1-bit). QE = 1 means flash operates in quad SPI mode (4 data lines active)
    input wire transaction_done, // From FSM
    input wire [7:0] noc_data,
    input wire noc_ready,
    input wire noc_valid,
    input wire [7:0] fsm_data,
    input wire fsm_ready,
    input wire fsm_valid,

    //outputs
    output wire r_w,
    output wire ena,
    output wire [7:0] fsm_opcode, // This should be 3:0, but I am not sure how it translates the 8 bit to 4 bit opcode
                                  // * Accept one command at a time from control/noc
                                  //* Translate it into opcode and pass it into transaction fsm/data port
    output wire [3:0] transaction_length,
    output wire out_ready,
    output wire out_valid
);

/* Accept one command at a time from control/noc
* Translate it into opcode and pass it into transaction fsm/data port
* Ack back when the operation ends (receive done from transaction fsm)
* Ignores any new command attempts while busy
*/

reg [1:0] sync_internal, sync_external;
always @(posedge clk or negedge rst_n) begin

    // Read data from NOC if not busy and if noc_valid
    if (noc_valid && )
    {

    }
    case (noc_data)
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