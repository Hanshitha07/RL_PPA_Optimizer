module fir_filter #(
    parameter integer DATA_WIDTH = 12,
    parameter integer PIPE_EN    = 1,
    parameter integer APPROX_COEFF = 0
)(
    input  wire                        clk,
    input  wire                        rst,
    input  wire signed [DATA_WIDTH-1:0] x_in,
    output reg  signed [DATA_WIDTH+3:0] y_out
);

    // Filter coefficients: exact vs. power-of-two shift-friendly approximation
    localparam signed [DATA_WIDTH-1:0] C0 = (APPROX_COEFF == 1) ? 4 : 3;
    localparam signed [DATA_WIDTH-1:0] C1 = (APPROX_COEFF == 1) ? 8 : 7;
    localparam signed [DATA_WIDTH-1:0] C2 = (APPROX_COEFF == 1) ? 8 : 7;
    localparam signed [DATA_WIDTH-1:0] C3 = (APPROX_COEFF == 1) ? 4 : 3;

    reg signed [DATA_WIDTH-1:0] d0, d1, d2, d3;
    wire signed [DATA_WIDTH+3:0] p0 = d0 * C0;
    wire signed [DATA_WIDTH+3:0] p1 = d1 * C1;
    wire signed [DATA_WIDTH+3:0] p2 = d2 * C2;
    wire signed [DATA_WIDTH+3:0] p3 = d3 * C3;

    reg signed [DATA_WIDTH+3:0] p0_r, p1_r, p2_r, p3_r;

    always @(posedge clk) begin
        if (rst) begin
            d0 <= 0; d1 <= 0; d2 <= 0; d3 <= 0;
            p0_r <= 0; p1_r <= 0; p2_r <= 0; p3_r <= 0;
            y_out <= 0;
        end else begin
            d0 <= x_in;
            d1 <= d0;
            d2 <= d1;
            d3 <= d2;

            if (PIPE_EN == 1) begin
                p0_r <= p0;
                p1_r <= p1;
                p2_r <= p2;
                p3_r <= p3;
                y_out <= p0_r + p1_r + p2_r + p3_r;
            end else begin
                y_out <= p0 + p1 + p2 + p3;
            end
        end
    end

endmodule