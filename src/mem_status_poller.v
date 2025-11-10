module status_poller (
    input  wire        clk,
    input  wire        rst_n,

    //----Transaction FSM Connections----
    input wire [7:0] in_total_transfers,

    input wire in_poller_start,
    
    input wire fsm_valid, //detect is fsm is valid so that a coplete transfer can be done
    
    input wire cmd_valid, //detect if cmd is ready to receive that data 

    // Ready to launch more work (used by FSM)
    output wire out_ready, //not ready unless (completed == total)

    // All transactions finished
    output wire all_done_valid,   // 1 = completed == total (no more work)
    
    output reg[6:0] statusRegister);

reg[7:0] completed_transfers;

always @(posedge clk or negedge rst_n)begin
    if (!rst_n) begin //if rst_n is 0 which means it is active
        completed_transfers <= 8'b0;
        statusRegister <= 7'b0;
    end
    else begin
        if (in_poller_start)begin
            completed_transfers <= 8'b0;
            statusRegister[4] <= 1'b0; //done is cleared
            statusRegister[5] <= 1'b1;//WE is now 1
            statusRegister[6] <= 1'b1; //QE is now 1
        end
        
        if(fsm_valid && cmd_valid)begin
            completed_transfers <= completed_transfers + 1'b1;
        end
        if (completed_transfers == in_total_transfers)begin
            statusRegister[4] <= 1'b1; //done is now signaled to 1
            statusRegister[5] <= 1'b0;//WE is now 0 as we are now done 
            statusRegister[6] <= 1'b0; //QE is now 0 as we are now done
        end
    end
end
    assign all_done_valid = (completed_transfers == in_total_transfers);
    assign out_ready = all_done_valid;
endmodule
