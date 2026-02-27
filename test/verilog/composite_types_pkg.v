// ============================================================================
// composite_types_pkg.v
// A realistic SystemVerilog package demonstrating enum, struct, union together.
//
// Scenario: A simple bus controller with:
//   - FSM states (enum)
//   - Bus request/response structs (struct, nested struct)
//   - Memory-mapped register overlay (union)
// ============================================================================

package bus_pkg;

    // --- Enum: FSM states for the bus controller ---
    typedef enum logic [2:0] {
        S_IDLE  = 3'd0,
        S_ADDR  = 3'd1,
        S_DATA  = 3'd2,
        S_RESP  = 3'd3,
        S_ERROR = 3'd4
    } bus_state_t;

    // --- Enum: Operation type ---
    typedef enum logic [1:0] {
        OP_READ  = 2'b00,
        OP_WRITE = 2'b01,
        OP_BURST = 2'b10,
        OP_IDLE  = 2'b11
    } bus_op_t;

    // --- Struct: Address descriptor ---
    typedef struct packed {
        logic [15:0] addr;
        logic [3:0]  byte_en;
        logic        write;
    } addr_desc_t;    // 21 bits

    // --- Struct: Bus request (nested struct) ---
    typedef struct packed {
        addr_desc_t  desc;
        logic [31:0] wdata;
    } bus_req_t;      // 21 + 32 = 53 bits

    // --- Struct: Bus response ---
    typedef struct packed {
        logic [29:0] rdata;
        logic        error;
        logic        valid;
    } bus_resp_t;     // 32 bits

    // --- Union: Register overlay ---
    typedef union packed {
        logic [31:0]  raw;
        bus_resp_t    as_resp;
    } reg_overlay_t;  // 32 bits (all members same width)

endpackage


// ============================================================================
// bus_master: Initiates bus transactions
// ============================================================================
module bus_master (
    input  logic               clk,
    input  logic               rst_n,
    input  bus_pkg::bus_op_t   op,
    input  logic [15:0]        target_addr,
    input  logic [31:0]        write_data,
    output bus_pkg::bus_state_t current_state,
    output bus_pkg::bus_req_t   req_out,
    input  bus_pkg::bus_resp_t  resp_in
);
    assign current_state = bus_pkg::S_IDLE;
    assign req_out = '0;
endmodule


// ============================================================================
// bus_slave: Responds to bus transactions
// ============================================================================
module bus_slave (
    input  logic                clk,
    input  logic                rst_n,
    input  bus_pkg::bus_req_t   req_in,
    output bus_pkg::bus_resp_t  resp_out,
    output bus_pkg::bus_state_t slave_state
);
    assign resp_out = '0;
    assign slave_state = bus_pkg::S_IDLE;
endmodule


// ============================================================================
// reg_block: Uses union for register overlay
// ============================================================================
module reg_block (
    input  logic                 clk,
    input  logic                 rst_n,
    input  bus_pkg::reg_overlay_t  reg_in,
    output bus_pkg::reg_overlay_t  reg_out,
    output logic [31:0]          raw_out
);
    assign reg_out = reg_in;
    assign raw_out = reg_in.raw;
endmodule
