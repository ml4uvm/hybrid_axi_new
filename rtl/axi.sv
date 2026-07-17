module axi4lite_slave (
    input wire ACLK,
    input wire ARESETN,

    // Write Address Channel
    input wire [7:0] AWADDR,
    input wire AWVALID,
    output reg AWREADY,

    // Write Data Channel
    input wire [31:0] WDATA,
    input wire WVALID,
    output reg WREADY,

    // Write Response Channel
    output reg [1:0] BRESP,
    output reg BVALID,
    input wire BREADY,

    // Read Address Channel
    input wire [7:0] ARADDR,
    input wire ARVALID,
    output reg ARREADY,

    // Read Data Channel
    output reg [31:0] RDATA,
    output reg [1:0] RRESP,
    output reg RVALID,
    input wire RREADY
);

    // --------------------------------------------------------
    // Parameters
    // --------------------------------------------------------
    localparam OKAY   = 2'b00;
    localparam SLVERR = 2'b10;

    // --------------------------------------------------------
    // Write FSM states
    // --------------------------------------------------------
    localparam WR_IDLE = 2'd0;
    localparam WR_ADDR = 2'd1;
    localparam WR_DATA = 2'd2;
    localparam WR_RESP = 2'd3;

    // --------------------------------------------------------
    // Read FSM states
    // --------------------------------------------------------
    localparam RD_IDLE = 2'd0;
    localparam RD_ADDR = 2'd1;
    localparam RD_DATA = 2'd2;

    // --------------------------------------------------------
    // Register file
    // --------------------------------------------------------
    reg [31:0] regfile [0:3];

    // --------------------------------------------------------
    // FSM state registers
    // --------------------------------------------------------
    reg [1:0] wr_state;
    reg [1:0] rd_state;

    // --------------------------------------------------------
    // Internal latched address
    // --------------------------------------------------------
    reg [7:0] wr_addr_lat;
    reg [7:0] rd_addr_lat;

    integer i;

    // --------------------------------------------------------
    // Write FSM
    // --------------------------------------------------------
    always @(posedge ACLK or negedge ARESETN) begin
        if (!ARESETN) begin
            wr_state    <= WR_IDLE;
            AWREADY     <= 0;
            WREADY      <= 0;
            BVALID      <= 0;
            BRESP       <= OKAY;
            wr_addr_lat <= 0;

            for (i = 0; i < 4; i = i + 1)
                regfile[i] <= 0;

        end else begin

            case (wr_state)

                // -----------------------------------------
                // IDLE: ready to accept write address
                // -----------------------------------------
                WR_IDLE: begin
                    AWREADY <= 1;
                    WREADY  <= 0;
                    BVALID  <= 0;

                    // Accept address only when both READY and VALID
                    // are high.
                    if (AWREADY && AWVALID) begin
                        wr_addr_lat <= AWADDR;
                        AWREADY     <= 0;
                        wr_state    <= WR_DATA;
                    end
                end

                // -----------------------------------------
                // WR_DATA: ready to accept write data
                // -----------------------------------------
                WR_DATA: begin
                    WREADY <= 1;

                    if (WREADY && WVALID) begin
                        WREADY <= 0;

                        // Write to register file if address is valid
                        if (wr_addr_lat < 4) begin
                            regfile[wr_addr_lat] <= WDATA;
                            BRESP <= OKAY;
                        end
                        else begin
                            BRESP <= SLVERR;
                        end

                        BVALID   <= 1;
                        wr_state <= WR_RESP;
                    end
                end
                                // -----------------------------------------
                // WR_RESP: hold response until master acks
                // -----------------------------------------
                WR_RESP: begin
                    if (BREADY) begin
                        BVALID   <= 0;
                        wr_state <= WR_IDLE;
                    end
                end

                default: begin
                    wr_state <= WR_IDLE;
                end

            endcase
        end
    end

    // --------------------------------------------------------
    // Read FSM
    // --------------------------------------------------------
    always @(posedge ACLK or negedge ARESETN) begin
        if (!ARESETN) begin
            rd_state    <= RD_IDLE;
            ARREADY     <= 0;
            RVALID      <= 0;
            RRESP       <= OKAY;
            RDATA       <= 0;
            rd_addr_lat <= 0;

        end else begin

            case (rd_state)

                // -----------------------------------------
                // IDLE: ready to accept read address
                // -----------------------------------------
                RD_IDLE: begin
                    ARREADY <= 1;
                    RVALID  <= 0;

                    // Accept read address only when READY and VALID
                    // are both high.
                    if (ARREADY && ARVALID) begin
                        rd_addr_lat <= ARADDR;
                        ARREADY     <= 0;
                        rd_state    <= RD_DATA;

                        // Latch response once when request is accepted.
                        if (ARADDR < 4) begin
                            RDATA <= regfile[ARADDR];
                            RRESP <= OKAY;
                        end
                        else begin
                            RDATA <= 32'hDEADBEEF;
                            RRESP <= SLVERR;
                        end
                    end
                end

                // -----------------------------------------
                // RD_DATA: present data until master accepts
                // -----------------------------------------
                RD_DATA: begin
                    RVALID <= 1;

                    if (RREADY) begin
                        RVALID   <= 0;
                        rd_state <= RD_IDLE;
                    end
                end

                default: begin
                    rd_state <= RD_IDLE;
                end

            endcase
        end
    end

endmodule