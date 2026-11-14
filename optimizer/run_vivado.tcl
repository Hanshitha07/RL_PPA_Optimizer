set out_dir [lindex $argv 0]

# Load parameters generated cleanly by Python
source "$out_dir/params.tcl"

foreach f $rtl_files {
    if {$f ne ""} { read_verilog $f }
}

set xdc_file "$out_dir/clock.xdc"
set fp [open $xdc_file w]
puts $fp "create_clock -period $clk_period -name sys_clk \[get_ports $clk_port\]"
close $fp
read_xdc $xdc_file

set synth_cmd [list synth_design -top $top_module -part $fpga_part]
foreach g $generics_list {
    lappend synth_cmd -generic $g
}
eval $synth_cmd

opt_design
place_design
route_design

report_timing_summary -file "$out_dir/timing.rpt"
report_utilization    -file "$out_dir/util.rpt"
report_power          -file "$out_dir/power.rpt"
exit