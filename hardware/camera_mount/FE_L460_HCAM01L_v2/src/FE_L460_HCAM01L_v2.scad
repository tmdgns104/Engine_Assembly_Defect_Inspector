// HARDWARE-CAD-001 | mm | PROTOTYPE; no guaranteed conveyor/stand fit.
// X: across belt, Y: travel, Z: up. 0 tilt = camera front faces DOWN.
PART = "assembly";
CAMERA_W = 87;                 // CONFIRMED body only
CAMERA_H = 37;                 // CONFIRMED body only
CAMERA_D = 33;                 // CONFIRMED body only
BELT_WIDTH = 100;              // CONFIRMED
CAMERA_CLEARANCE = 1.2;        // PROVISIONAL total, 0.6 mm each side
CRADLE_WALL = 5;              // R2 has room without semicircle/tangent slivers
CAMERA_MOUNT_THREAD_STANDARD = "PROVISIONAL_UNVERIFIED";
CAMERA_MOUNT_SLOT = 8;         // PROVISIONAL clearance, NOT a thread
CAMERA_MOUNT_TRAVEL = 56;      // full slot length, centre travel 48
CRADLE_FIX_X = 24;            // keeps fallback M6 nuts outside fork cheeks
FOLDED_STAND_GAP = 12;         // PROVISIONAL visual envelope, NOT measured
FRAME_THICKNESS = 12;          // PROVISIONAL clamp setup, not FE-L460 spec
FRAME_LIP_DEPTH = 26;          // PROVISIONAL available engagement assumption
RUBBER_PAD = 1;                // PROVISIONAL each opposing face
CROSSBAR_LENGTH = 180;
POST_SPACING = 148;            // PROVISIONAL frame spacing
UPRIGHT_HEIGHT = 230;
HEIGHT_LOWER = 84;             // lower bolt centre, upper bolt = lower+24
HEIGHT_UPPER = 184;
HEIGHT_POSITION = 134;
CAMERA_SLIDE = 0;              // +/-50 design operating limit
TILT = 0;                     // physical design range -15 to +30 deg
M6_CLEARANCE = 6.8;            // PROVISIONAL FDM through bore, no printed threads
HINGE_GAP = 14.4;              // 12 lug + two 1 mm steel washers + 0.4 play
HINGE_LUG = 12;
EDGE_R = 4;
SMALL_R = 2.5;
PIVOT_Y = 46;                 // 2 mm lug/backplate gap at lowered pivot
PIVOT_Z = 40.5;                // lower hinge, preserves access behind mount slot
CAMERA_Z = 24;                // PROVISIONAL body reference centre above hinge
PLATE_BACK = 60;
PLATE_FRONT = 68;
PLATE_SLOT_Z = 24;
CI_W = CAMERA_W + CAMERA_CLEARANCE;
CI_H = CAMERA_H + CAMERA_CLEARANCE;
CI_D = CAMERA_D + CAMERA_CLEARANCE;
CRADLE_FIX_DEPTH = CI_D/2;
$fn = 48;
EPS = 0.05;
GAUGE_EPS = 0.02;             // CSG boundary tolerance ONLY, dimensions audited separately

assert(CROSSBAR_LENGTH >= POST_SPACING+28);
assert(abs(CAMERA_SLIDE)<=50 && TILT>=-15 && TILT<=30);
assert(HEIGHT_POSITION>=HEIGHT_LOWER && HEIGHT_POSITION<=HEIGHT_UPPER);
assert(UPRIGHT_HEIGHT>=HEIGHT_UPPER+24+20);
assert(FRAME_THICKNESS>=6 && FRAME_THICKNESS<=20);
assert(FRAME_LIP_DEPTH>=22 && FRAME_LIP_DEPTH<=40);

// Rounded in-plane external corners, plus small top/bottom chamfers.
// Flat mating lands retained; avoid costly whole-part Minkowski.
module rounded_rect(w,h,r) {
    hull() for(x=[r,w-r],y=[r,h-r]) translate([x,y]) circle(r=r);
}
module soft_box(s,r=EDGE_R,c=0.7) {
    hull() {
        linear_extrude(0.02) offset(delta=-c) rounded_rect(s[0],s[1],r);
        translate([0,0,c]) linear_extrude(s[2]-2*c) rounded_rect(s[0],s[1],r);
        translate([0,0,s[2]-0.02]) linear_extrude(0.02)
            offset(delta=-c) rounded_rect(s[0],s[1],r);
    }
}
module xz_plate(w,h,t,r=EDGE_R) {
    translate([-w/2,0,0]) rotate([90,0,0]) soft_box([w,h,t],r);
}
module y_hole(x,z,d=M6_CLEARANCE) {
    translate([x,-80,z]) rotate([-90,0,0]) cylinder(h=240,d=d);
}
module y_slot(x1,z1,x2,z2,d=M6_CLEARANCE) {
    hull() { y_hole(x1,z1,d); y_hole(x2,z2,d); }
}
module z_hole(x,y,d=M6_CLEARANCE) {
    translate([x,y,-80]) cylinder(h=200,d=d);
}
module x_hole(y,z,d=M6_CLEARANCE) {
    translate([-100,y,z]) rotate([0,90,0]) cylinder(h=200,d=d);
}

module upright() {
    difference() {
        union() {
            xz_plate(32,UPRIGHT_HEIGHT,14);
            // Widened rounded root: two clamping bolts, no cantilever thin tab.
            hull() {
                xz_plate(40,42,14);
                translate([0,0,42]) xz_plate(32,22,14);
            }
        }
        y_hole(0,12); y_hole(0,36);
        y_slot(0,HEIGHT_LOWER,0,HEIGHT_UPPER+24);
        // Shallow reference ticks on front. They are not calibrated optical height.
        for(z=[84:10:184]) translate([7,-0.5,z-0.4]) cube([6,1,0.8]);
    }
}
module crossbar() {
    difference() {
        translate([0,18,0]) xz_plate(CROSSBAR_LENGTH,48,18);
        for(x=[-POST_SPACING/2,POST_SPACING/2],z=[12,36]) y_hole(x,z);
        for(z=[12,36]) y_slot(-54,z,54,z);
    }
}
module clamp_body(coupon=false) {
    length_y = coupon ? 20 : 64;
    stations = coupon ? [0] : [-22,22];
    difference() {
        union() {
            translate([2-FRAME_LIP_DEPTH,-length_y/2,-10]) soft_box([FRAME_LIP_DEPTH+22,length_y,10]);
            if(!coupon) {
                translate([0,10,0]) xz_plate(40,48,10);
                // Two gussets; triangle lies in the principal vertical load plane.
                for(x=[-19,13]) translate([x,0,0])
                    rotate([90,0,90]) linear_extrude(6)
                        polygon([[8,-1],[27,-1],[8,39]]);
            }
        }
        for(y=stations) z_hole(16,y);
        if(!coupon) { y_hole(0,12); y_hole(0,36); }
    }
}
module clamp_jaw(coupon=false) {
    length_y = coupon ? 20 : 64;
    difference() {
        translate([2-FRAME_LIP_DEPTH,-length_y/2,0]) soft_box([FRAME_LIP_DEPTH+22,length_y,10]);
        for(y=coupon ? [0] : [-22,22]) z_hole(16,y);
    }
}
module fork_cheek() {
    // Extrudes along X. Circular end and broad tapered root avoid sharp tabs.
    rotate([90,0,90]) linear_extrude(8)
        hull() {
            translate([PIVOT_Y,PIVOT_Z]) circle(r=12);
            translate([23,30]) circle(r=5);
            translate([23,42]) circle(r=5);
        }
}
module carriage() {
    difference() {
        union() {
            translate([0,28,0]) xz_plate(40,48,10);
            translate([HINGE_GAP/2,0,0]) fork_cheek();
            translate([-HINGE_GAP/2-8,0,0]) fork_cheek();
            // Cable tie lug: two wide slots, no assumed camera cable exit point.
            translate([17,28,18]) xz_plate(38,24,10);
        }
        for(z=[12,36]) y_hole(0,z);
        x_hole(PIVOT_Y,PIVOT_Z);
        for(x=[25,32]) y_slot(x,25,x,35,3.2);
        // Visible 0-degree reference line on outer cheek, align to plate mark.
        translate([HINGE_GAP/2+7.5,PIVOT_Y,PIVOT_Z-0.4]) cube([1,11,0.8]);
    }
}
module camera_plate(coupon=false) {
    difference() {
        union() {
            translate([0,PLATE_FRONT,-14]) xz_plate(104,56,8,3);
            if(!coupon) {
                translate([-HINGE_LUG/2,PIVOT_Y,0]) rotate([0,90,0]) cylinder(h=HINGE_LUG,r=16);
                translate([-HINGE_LUG/2,PIVOT_Y,-14]) cube([HINGE_LUG,PLATE_FRONT-PIVOT_Y,28]);
            }
        }
        y_slot(-(CAMERA_MOUNT_TRAVEL-CAMERA_MOUNT_SLOT)/2,PLATE_SLOT_Z,
                (CAMERA_MOUNT_TRAVEL-CAMERA_MOUNT_SLOT)/2,PLATE_SLOT_Z,CAMERA_MOUNT_SLOT);
        for(x=[-45,45]) y_slot(x,0,x,16,4);
        if(!coupon) x_hole(PIVOT_Y,0);
        translate([50,PLATE_BACK-1,-0.4]) cube([3,10,0.8]);
    }
}
module cradle() {
    // Optional body-only fit cradle. Camera front is +Y; no front or roof wall.
    difference() {
        union() {
            translate([-CI_W/2-CRADLE_WALL,-CRADLE_WALL,0]) soft_box([CI_W+2*CRADLE_WALL,CI_D+CRADLE_WALL,10],3);
            for(x=[-CI_W/2-CRADLE_WALL,CI_W/2])
                translate([x,-CRADLE_WALL,9]) soft_box([CRADLE_WALL,CI_D+CRADLE_WALL,CI_H+1],2,0.4);
            translate([-CI_W/2-CRADLE_WALL,-CRADLE_WALL,9]) soft_box([CI_W+2*CRADLE_WALL,CRADLE_WALL,9],2,0.4);
        }
        // Exact open rectangular interior. This also prevents rounded-wall intrusion.
        translate([-CI_W/2,0,10]) cube([CI_W,CI_D+10,CI_H+10]);
        for(x=[-CRADLE_FIX_X,CRADLE_FIX_X]) {
            z_hole(x,CRADLE_FIX_DEPTH);
            translate([x,CRADLE_FIX_DEPTH,6]) cylinder(h=5,d=12); // button-head recess
        }
        for(x=[-38,38]) translate([x-5,3.5,-1]) cube([10,3,12]);
    }
}
module body_gauge(clearance=false) {
    // Avoid exporting zero-thickness coplanar contacts as invalid 'intersection STL'.
    w=clearance ? CI_W-2*GAUGE_EPS : CAMERA_W;
    d=clearance ? CI_D-2*GAUGE_EPS : CAMERA_D;
    h=clearance ? CI_H-2*GAUGE_EPS : CAMERA_H;
    translate([-w/2,clearance ? GAUGE_EPS : CAMERA_CLEARANCE/2,10+GAUGE_EPS]) cube([w,d,h]);
}
module camera_dummy() {
    // Envelope ONLY. Front face is down; actual lens centre/stand not invented.
    translate([-CAMERA_W/2,PLATE_FRONT+FOLDED_STAND_GAP,CAMERA_Z-CAMERA_D/2])
        cube([CAMERA_W,CAMERA_H,CAMERA_D]);
}
module tilted_group() {
    translate([CAMERA_SLIDE,0,HEIGHT_POSITION-12+PIVOT_Z])
        translate([0,PIVOT_Y,0]) rotate([TILT,0,0]) translate([0,-PIVOT_Y,0]) children();
}
module structure() {
    for(side=[-1,1]) {
        translate([side*POST_SPACING/2,0,0]) upright();
        translate([side*POST_SPACING/2,0,0]) scale([side,1,1]) clamp_body();
        translate([side*POST_SPACING/2,0,-20-FRAME_THICKNESS-2*RUBBER_PAD])
            scale([side,1,1]) clamp_jaw();
    }
    translate([0,0,HEIGHT_POSITION-12]) crossbar();
    translate([CAMERA_SLIDE,0,HEIGHT_POSITION-12]) carriage();
}
module arrow_down() {
    cylinder(h=40,r=1.5);
    translate([0,0,-10]) cylinder(h=10,r1=0,r2=5);
}
module assembly() {
    color("SteelBlue") structure();
    color("DarkOrange") tilted_group() camera_plate();
    color([0.15,0.17,0.2,1]) tilted_group() camera_dummy();
    color([0.1,0.65,0.8,1]) tilted_group()
        translate([-CAMERA_W/2,PLATE_FRONT+FOLDED_STAND_GAP,CAMERA_Z-CAMERA_D/2-0.1])
            cube([CAMERA_W,CAMERA_H,0.1]); // whole front-plane reference, not a lens location
    color([0.8,0.6,0.2,0.35]) tilted_group()
        translate([-25,PLATE_FRONT,CAMERA_Z-6]) cube([50,FOLDED_STAND_GAP,20]);
    // Belt and frame are conceptual reference envelopes, NOT FE-L460 CAD.
    color([0.2,0.35,0.28,0.55]) translate([-BELT_WIDTH/2,-45,-3]) cube([BELT_WIDTH,240,3]);
    for(side=[-1,1]) color([0.5,0.5,0.5,0.35])
        translate([side*POST_SPACING/2,0,-10-RUBBER_PAD-FRAME_THICKNESS])
            scale([side,1,1]) translate([4-FRAME_LIP_DEPTH,-32,0]) cube([FRAME_LIP_DEPTH,64,FRAME_THICKNESS]);
    color("Crimson") tilted_group()
        translate([0,PLATE_FRONT+FOLDED_STAND_GAP+CAMERA_H/2,CAMERA_Z-CAMERA_D/2-55]) arrow_down();
    color("Black") translate([80,155,1]) rotate([0,0,180]) linear_extrude(0.5)
        text("TOP-DOWN / 100 mm BELT",size=6);
    color("Black") translate([75,180,1]) rotate([0,0,180]) linear_extrude(0.5)
        text("BODY 87 x 37 x 33 / REFERENCE",size=5);
}

// Export print parts already oriented on Z=0. One solid per output file.
if(PART=="upright") translate([20,UPRIGHT_HEIGHT,14]) rotate([90,0,0]) upright();
else if(PART=="crossbar") translate([CROSSBAR_LENGTH/2,48,0]) rotate([90,0,0]) crossbar();
else if(PART=="clamp_body") translate([10,32,24]) rotate([0,90,0]) clamp_body();
else if(PART=="clamp_body_left") translate([10,32,FRAME_LIP_DEPTH-2]) rotate([0,90,0]) mirror([1,0,0]) clamp_body();
else if(PART=="clamp_jaw") translate([FRAME_LIP_DEPTH-2,32,0]) clamp_jaw();
else if(PART=="camera_carriage") translate([20,PIVOT_Z+12,-18]) rotate([90,0,0]) carriage();
else if(PART=="camera_mount_plate") translate([52,16,PLATE_FRONT]) rotate([-90,0,0]) camera_plate();
else if(PART=="camera_cradle_HCAM01L") translate([CI_W/2+CRADLE_WALL,CRADLE_WALL,0]) cradle();
else if(PART=="clamp_fit_coupon") translate([FRAME_LIP_DEPTH-2,10,10]) clamp_body(true);
else if(PART=="clamp_fit_coupon_jaw") translate([FRAME_LIP_DEPTH-2,10,0]) clamp_jaw(true);
else if(PART=="camera_mount_fit_coupon") translate([52,14,PLATE_FRONT]) rotate([-90,0,0]) camera_plate(true);
else if(PART=="clearance_intersection") intersection() { cradle(); body_gauge(true); }
// Fixed bar/posts are behind Y=18; clamps below Z=48. Analytic margins are
// independently checked by build_validate.py. Only carriage is a near obstacle.
else if(PART=="tilt_intersection") intersection() {
    translate([CAMERA_SLIDE,0,HEIGHT_POSITION-12]) carriage();
    tilted_group() { camera_plate(); camera_dummy(); }
}
else if(PART=="assembly") assembly();
else assert(false,"Unknown PART");
