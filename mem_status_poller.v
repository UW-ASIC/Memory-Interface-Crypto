// Welcome to JDoodle!
//
// You can execute code here in 88 languages. Right now you’re in the Verilog IDE. 
//
//  1. Click the orange Execute button ️▶ to execute the sample code below and see how it works.
//  2. Want help writing or debugging code? Type a query into JDroid on the right hand side ---------------->
//  3. Try the menu buttons on the left. Save your file, share code with friends and open saved projects.
//
// Want to change languages? Try the search bar up the top.

module status_poller(
    input wire clk,
    
    input wire rst_n, //reset when low (on when low)
    
    input wire swdo,
    
    input wire lwdo,
    
    input wire gwdo,
    
    input wire gwdo_enable,
    
    input wire cs_deassert, //need to figure this out
    
    input wire length[8:0], //importance of length
    
    input wire ena,
    
    input wire status_fsm[6:0], // WE, QE, Done, Mode[1], mode[0], reserved[1], reserved[0] MSB to LSB
    
    input wire timeouterrhandling, //idrk what this does
    
    output wire done,
    
    output reg status_to_cu[6:0], //what status bits are important? currently going to assume 1 is valid
    
//assumed roles of the status
    
    output reg status_to_qspi[6:0],
    
    output reg sdwo_timeout,
    
    output reg lwdo_timeout,
    
    output reg gwdo_timeout
    
    );
    
    localparam swdo_threshold = 15;
    localparam lwdo_threshold = 30;
    localparam gwdo_threshold = 45;
    reg [23:0] swdo_timer;
    reg [23:0] lwdo_timer;
    reg [23:0] gwdo_timer;
    reg [7:0]  lwdoresetcounter;
    
    always @(posedge clk or negedge rst_n)begin
    if (!rst_n) begin //if rst_n is 0 which means it is active
        lwdo_timer <= 0;
        swdo_timer <= 0;
        gwdo_timer <= 0;
        lwdoresetcounter <= 0;
        swdo_timeout <= 0;
        lwdo_timeout <= 0;
        gwdo_timeout <= 0;
        done <= 0;
    end else begin
        if (!cs_deassert & ena) begin//only runs when enabled by cu and not deasserted by qspi
            status_to_cu <= status_fsm; 
            status_to_qspi <= status_fsm; //assign the status of things that are going out
            swdo_timer <= swdo_timer+1;
            lwdo_timer <= lwdo_timer+1;
            gwdo_timer <= gwdo_timer+1;
        end
        if (swdo & !status_fsm[2])begin
            if(swdo_timer > swdo_threshold)begin
                swdo_timeout <= 1'b1;
                swdo_timer <= 0;
            end
        end
        if (lwdo & !status_fsm[2])begin
            if(lwdo_timer >lwdo_threshold)begin
                lwdoresetcounter <= lwdoresetcounter+1;
                lwdo_timer <= 0;
            end
            if(lwdoresetcounter == 1)begin
                lwdo_timeout <= 1'b1; //upper limit is reached and pulse is sent
                lwdo_timer <= 0;
            end
        
        end
        if(gwdo & !status_fsm[2])begin
            if(gwdo_timer > gwdo_threshold)begin
                gwdo_timeout <=1'b1;
                gwdo_timer <= 0;
            end
        end
        /*
        if(gwdo_enable == 1)begin
            gwdo_timeout <= 1'b1;
        end
        idk what gwdo enable is used for 
        */ 
        done <= status_fsm[2];
        if (status_fsm[2] == 1) begin
            swdo_timer <= 0;
            lwdo_timer <= 0;
            gwdo_timer <= 0;
            lwdoresetcounter <= 0;
    end
    end
      
endmodule
