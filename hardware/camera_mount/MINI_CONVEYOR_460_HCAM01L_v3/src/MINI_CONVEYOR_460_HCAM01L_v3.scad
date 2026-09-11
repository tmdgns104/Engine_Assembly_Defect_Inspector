// HARDWARE-CAD-002 + 003 | mm | X across belt, Y travel, Z up from table.
// PROTOTYPE: digital dimensions are not physical fit/load/optical qualification.
PART = "assembly";
CONVEYOR_LENGTH = 460;         // CONFIRMED_USER_DRAWING, user transcription
BELT_WIDTH = 85;
CONVEYOR_OUTER_WIDTH = 118;
CONVEYOR_SIDE_HEIGHT = 22.7;
MOTOR_END_MAX_HEIGHT = 55.5;
CONVEYOR_BOTTOM_Z = 0;         // PROVISIONAL reference ONLY, actual belt datum unknown
MOTOR_REF_LENGTH = 70;         // PROVISIONAL envelope, not ambiguous drawing '60'
CAMERA_W = 87;                 // CONFIRMED body excluding stand
CAMERA_H = 37;
CAMERA_D = 33;
CAMERA_CLEARANCE = 1.2;        // PROVISIONAL total / 0.6 each side
POCKET_DEPTH = 2.5;
LENS_WINDOW_D = 30;            // PROVISIONAL top diameter; bottom flares automatically
CAMERA_HFOV = 90;             // PROVISIONAL_DESIGN_ENVELOPE, not HCAM01L specification
CAMERA_VFOV = 70;             // PROVISIONAL_DESIGN_ENVELOPE / REQUIRES_MEASUREMENT
OPTICAL_ORIGIN_ABOVE_SUPPORT = 3; // PROVISIONAL pupil reference, not ring tip
OPTICAL_ORIGIN_MARGIN_XY = 2;  // PROVISIONAL origin uncertainty, per side
OPTICAL_CLEARANCE_MARGIN = 5; // mm normal to lateral FOV planes; no rearward extension
OPTICAL_TARGET_Z = 0;         // table plane, includes provisional belt surface
INSPECTION_ZONE_W = 85;       // reference only, actual coverage requires camera test
INSPECTION_ZONE_L = 120;      // PROVISIONAL inspection area, not engine dimensions
SHOW_FOV = true;              // assembly only; never included in printable PARTs
LENS_RING_ESTIMATE_D = 22;     // PHOTO_ESTIMATE, not metrology
LENS_OFFSET_X = 0;             // PHOTO_ESTIMATE / adjustable
LENS_OFFSET_Y = 0;
LENS_PROTRUSION_REF = 4;       // PROVISIONAL visualization, not measured
PAD_T = 1;                    // PROVISIONAL soft pad, four outer lands
UPRIGHT_WIDTH = 36;
UPRIGHT_THICKNESS = 14;
RAIL_LENGTH = 300;            // USER REVISION: two full-length uprights, no lap joint
RAIL_BOTTOM_Z = 10;
HEIGHT_HOLE_DIAMETER = 6.8;
HEIGHT_HOLE_PITCH = 15;
FIRST_HEIGHT_Z = 77.5;        // deck contact plane reaches exactly table Z300 at index12
HEIGHT_HOLE_COUNT = 15;
LOWER_INDEX = 7;              // allowed 2..12; upper bolt uses lower+3
PORTAL_INNER_CLEAR_WIDTH = 160;
BASE_MOUNT_HOLE_D = 6.5;       // PROVISIONAL, table screw standard UNKNOWN
BASE_W = 80;
BASE_L = 70;
BASE_T = 10;
BAR_T = 18;
BAR_H = 61;
BAR_BOLT_Z = 8;
BAR_BOLT_SEPARATION = 45;
CAMERA_SLIDE = 0;             // +/-30 operating range
DECK_BACK_T = 10;
DECK_W = 112;
DECK_BOTTOM_Z = 60;
DECK_T = 8;
CAMERA_Y = 255;               // rear Portal -> Conveyor central inspection zone
COUPON_REAR_OFFSET = 34;
STOP_EXTRA_H = 1.5;           // 4 mm above contact plane (2.5+1.5)
EDGE_R = 4;
GAUGE_EPS = 0.02;
$fn = 64;

POST_X = (PORTAL_INNER_CLEAR_WIDTH+UPRIGHT_WIDTH)/2;
BAR_LENGTH = 2*POST_X+UPRIGHT_WIDTH;
HOLE_Z = [for(i=[0:HEIGHT_HOLE_COUNT-1]) FIRST_HEIGHT_Z+i*HEIGHT_HOLE_PITCH];
LOWER_Z = HOLE_Z[LOWER_INDEX-1];
BAR_Z = LOWER_Z-BAR_BOLT_Z;
CI_W = CAMERA_W+CAMERA_CLEARANCE;
CI_H = CAMERA_H+CAMERA_CLEARANCE;
DECK_TOP = DECK_BOTTOM_Z+DECK_T;
CONTACT_Z = DECK_TOP-POCKET_DEPTH;
BODY_Z = CONTACT_Z+PAD_T;
DECK_FRONT_Y = CAMERA_Y+30;
COUPON_START_Y = CAMERA_Y-COUPON_REAR_OFFSET;
FOV_TX = tan(CAMERA_HFOV/2);
FOV_TY = tan(CAMERA_VFOV/2);
WINDOW_FLARE_SLOPE = sqrt(FOV_TX*FOV_TX+FOV_TY*FOV_TY);
LENS_WINDOW_BOTTOM_D = LENS_WINDOW_D+2*DECK_T*WINDOW_FLARE_SLOPE;
assert(LOWER_INDEX>=2 && LOWER_INDEX<=HEIGHT_HOLE_COUNT-3);
assert(abs(CAMERA_SLIDE)<=30);
assert(BAR_BOLT_SEPARATION==3*HEIGHT_HOLE_PITCH);
assert(UPRIGHT_THICKNESS>=14 && UPRIGHT_WIDTH>=36);
assert(abs(LENS_OFFSET_X)+LENS_WINDOW_D/2<CI_W/2-4);
assert(abs(LENS_OFFSET_Y)+LENS_WINDOW_D/2<CI_H/2-1);
assert(CAMERA_HFOV>0 && CAMERA_HFOV<150 && CAMERA_VFOV>0 && CAMERA_VFOV<150);
assert(OPTICAL_CLEARANCE_MARGIN>=5);
assert(LENS_WINDOW_BOTTOM_D/2+abs(LENS_OFFSET_Y)<29);

module lens_window() {
    // Exact diameter30 at Deck top; grows toward conveyor. Extended only for Boolean cut.
    translate([LENS_OFFSET_X,CAMERA_Y+LENS_OFFSET_Y,DECK_BOTTOM_Z-1])
        cylinder(h=DECK_T+2,r1=LENS_WINDOW_D/2+(DECK_T+1)*WINDOW_FLARE_SLOPE,
                 r2=LENS_WINDOW_D/2-WINDOW_FLARE_SLOPE);
}
module camera_fov_reference(margin=OPTICAL_CLEARANCE_MARGIN) {
    origin_z=BAR_Z+CONTACT_Z+OPTICAL_ORIGIN_ABOVE_SUPPORT;
    depth=origin_z-OPTICAL_TARGET_Z;
    hx=OPTICAL_ORIGIN_MARGIN_XY+margin*sqrt(1+FOV_TX*FOV_TX);
    hy=OPTICAL_ORIGIN_MARGIN_XY+margin*sqrt(1+FOV_TY*FOV_TY);
    assert(depth>0 && hx>0 && hy>0);
    translate([CAMERA_SLIDE+LENS_OFFSET_X,CAMERA_Y+LENS_OFFSET_Y,OPTICAL_TARGET_Z])
        linear_extrude(depth,scale=[hx/(hx+depth*FOV_TX),hy/(hy+depth*FOV_TY)])
            square([2*(hx+depth*FOV_TX),2*(hy+depth*FOV_TY)],center=true);
}

module rounded_rect(w,h,r) {
    hull() for(x=[r,w-r],y=[r,h-r]) translate([x,y]) circle(r=r);
}
module soft_box(s,r=EDGE_R,c=0.6) {
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
module y_hole(x,z,d=HEIGHT_HOLE_DIAMETER) {
    translate([x,-40,z]) rotate([-90,0,0]) cylinder(h=170,d=d);
}
module y_slot(x1,z1,x2,z2,d=HEIGHT_HOLE_DIAMETER) {
    hull() { y_hole(x1,z1,d); y_hole(x2,z2,d); }
}
module z_hole(x,y,d) { translate([x,y,-10]) cylinder(h=150,d=d); }
module z_slot(x,y1,y2,d) { hull() {z_hole(x,y1,d); z_hole(x,y2,d);} }
module rail(coupon=false) {
    start = RAIL_BOTTOM_Z;
    length = coupon ? 65 : RAIL_LENGTH;
    difference() {
        xz_plate(UPRIGHT_WIDTH,length,UPRIGHT_THICKNESS);
        for(z=coupon ? [10:15:55] : [for(h=HOLE_Z) if(h>start+5 && h<start+RAIL_LENGTH-5) h-start]) {
            y_hole(0,z);
            // Small entry chamfer on both outer faces.
            translate([0,0.01,z]) rotate([90,0,0]) cylinder(h=0.61,d1=8,d2=HEIGHT_HOLE_DIAMETER);
            translate([0,-UPRIGHT_THICKNESS-0.01,z]) rotate([-90,0,0]) cylinder(h=0.61,d1=8,d2=HEIGHT_HOLE_DIAMETER);
        }
        if(!coupon) { y_hole(0,20); y_hole(0,50); }
        if(!coupon) for(i=[0:HEIGHT_HOLE_COUNT-1]) if(HOLE_Z[i]>start+5 && HOLE_Z[i]<start+RAIL_LENGTH-5)
            translate([8,-0.4,HOLE_Z[i]-start-0.35]) cube([(i%5==0)?7:4,0.8,0.7]);
    }
}
module base() {
    difference() {
        union() {
            translate([-UPRIGHT_WIDTH/2,-40,0]) soft_box([BASE_W,BASE_L,BASE_T],6);
            translate([0,10,9]) xz_plate(36,63,10);
            for(x=[-17,11]) translate([x,0,0]) rotate([90,0,90]) linear_extrude(6)
                polygon([[8,9],[29,9],[8,65]]);
        }
        for(x=[0,50],y=[-28,20]) {
            z_hole(x,y,BASE_MOUNT_HOLE_D);
            translate([x,y,9.3]) cylinder(h=0.8,d1=BASE_MOUNT_HOLE_D,d2=BASE_MOUNT_HOLE_D+1.4);
        }
        y_hole(0,30); y_hole(0,60);
    }
}
module bar() {
    difference() {
        translate([0,BAR_T,0]) xz_plate(BAR_LENGTH,BAR_H,BAR_T);
        for(x=[-POST_X,POST_X]) {
            y_hole(x,BAR_BOLT_Z); y_hole(x,BAR_BOLT_Z+BAR_BOLT_SEPARATION);
        }
        for(z=[BAR_BOLT_Z,BAR_BOLT_Z+BAR_BOLT_SEPARATION]) y_slot(-30,z,30,z);
    }
}
module contact_lands(h=2) {
    for(x=[-35,35],y=[CAMERA_Y-12,CAMERA_Y+12])
        translate([x-5,y-3,CONTACT_Z-1]) cube([10,6,h]);
}
module deck(coupon=false) {
    difference() {
        union() {
            translate([-DECK_W/2,coupon?COUPON_START_Y:BAR_T,DECK_BOTTOM_Z])
                soft_box([DECK_W,DECK_FRONT_Y-(coupon?COUPON_START_Y:BAR_T),DECK_T]);
            if(!coupon) {
                translate([0,BAR_T+DECK_BACK_T,0]) xz_plate(92,BAR_H,DECK_BACK_T);
                for(x=[-40,34]) translate([x,0,0]) rotate([90,0,90]) linear_extrude(6)
                    polygon([[24,15],[24,61],[CAMERA_Y+21,61]]);
            }
            // Low stops, rounded external ends. Pocket cut keeps exact clear rectangle.
            // Rear and side stops have a small plan-view gap; no tangent-only seam.
            for(x=[-CI_W/2-4,CI_W/2]) translate([x,CAMERA_Y-CI_H/2+1.2,DECK_TOP-1])
                soft_box([4,CI_H-2.4,1+STOP_EXTRA_H],2,0.3);
            translate([-CI_W/2-4,CAMERA_Y-CI_H/2-4,DECK_TOP-1])
                soft_box([CI_W+8,4,1+STOP_EXTRA_H],2,0.3);
        }
        translate([-CI_W/2,CAMERA_Y-CI_H/2,CONTACT_Z]) cube([CI_W,CI_H,45]);
        difference() {
            translate([-CI_W/2,CAMERA_Y-CI_H/2,CONTACT_Z-1]) cube([CI_W,CI_H,2]);
            contact_lands(4);
        }
        lens_window();
        // Retention underpass stays in the rear band, never across the optical window.
        for(x=[-51,51]) z_slot(x,CAMERA_Y-30,CAMERA_Y-16,3.6);
        if(!coupon) {
            for(z=[BAR_BOLT_Z,BAR_BOLT_Z+BAR_BOLT_SEPARATION]) y_hole(0,z);
            for(x=[45,51]) z_slot(x,CAMERA_Y-49,CAMERA_Y-41,3);
        }
    }
}
module base_coupon() {
    difference() {
        soft_box([34,34,BASE_T],5);
        z_hole(17,17,BASE_MOUNT_HOLE_D);
        translate([17,17,9.3]) cylinder(h=0.8,d1=BASE_MOUNT_HOLE_D,d2=BASE_MOUNT_HOLE_D+1.4);
    }
}
module conveyor() {
    translate([-CONVEYOR_OUTER_WIDTH/2,CAMERA_Y-CONVEYOR_LENGTH/2,CONVEYOR_BOTTOM_Z])
        cube([CONVEYOR_OUTER_WIDTH,CONVEYOR_LENGTH,CONVEYOR_SIDE_HEIGHT]);
}
module motor_ref() {
    translate([-CONVEYOR_OUTER_WIDTH/2,CAMERA_Y+CONVEYOR_LENGTH/2-MOTOR_REF_LENGTH,CONVEYOR_BOTTOM_Z])
        cube([CONVEYOR_OUTER_WIDTH,MOTOR_REF_LENGTH,MOTOR_END_MAX_HEIGHT]);
}
module rails() {
    for(side=[-1,1]) {
        translate([side*POST_X,0,RAIL_BOTTOM_Z]) rail();
    }
}
module bases() { for(side=[-1,1]) translate([side*POST_X,0,0]) scale([side,1,1]) base(); }
module deck_pose() { translate([CAMERA_SLIDE,0,BAR_Z]) children(); }
module body(inset=0) {
    translate([-CAMERA_W/2+inset,CAMERA_Y-CAMERA_H/2+inset,BODY_Z+inset])
        cube([CAMERA_W-2*inset,CAMERA_H-2*inset,CAMERA_D-2*inset]);
}
module lens() {
    translate([LENS_OFFSET_X,CAMERA_Y+LENS_OFFSET_Y,BODY_Z-LENS_PROTRUSION_REF])
        cylinder(h=LENS_PROTRUSION_REF,d=LENS_RING_ESTIMATE_D);
}
module cable() {
    // Camera rear/top -> rear deck tie points -> Crossbar rear -> right Upright rear.
    // Illustrative retained route; exit, bending radius and folded stand require measurement.
    points=[[30,CAMERA_Y-10,BODY_Z+CAMERA_D+2],[42,CAMERA_Y-17,117],
        [48,CAMERA_Y-30,110],[48,CAMERA_Y-45,76],[0,80,76],[0,-22,76],[POST_X-CAMERA_SLIDE,-22,76]];
    for(i=[0:len(points)-2]) hull() for(p=[points[i],points[i+1]]) translate(p) sphere(r=2,$fn=20);
}
module cable_tail() {
    hull() for(z=[20,BAR_Z+76]) translate([POST_X,-22,z]) sphere(r=2,$fn=20);
}
module strap() {
    // Conservative10 mm-wide routing envelope. Under-deck bridge uses rear band only.
    points=[[-51,CAMERA_Y-25,DECK_BOTTOM_Z-1],[-51,CAMERA_Y-25,DECK_TOP+1],
        [-47,CAMERA_Y-10,BODY_Z+CAMERA_D+2],[47,CAMERA_Y-10,BODY_Z+CAMERA_D+2],
        [51,CAMERA_Y-25,DECK_TOP+1],[51,CAMERA_Y-25,DECK_BOTTOM_Z-1],
        [-51,CAMERA_Y-25,DECK_BOTTOM_Z-1]];
    for(i=[0:len(points)-2]) hull() for(p=[points[i],points[i+1]])
        translate(p-[1,5,0.7]) cube([2,10,1.4]);
}
module table_fasteners() {
    for(s=[-1,1],x=[0,50],y=[-28,20]) translate([s*(POST_X+x),y,-5]) {
        cylinder(h=15,d=6);
        translate([0,0,15]) cylinder(h=5,d=12);
    }
}
module structure() { bases(); rails(); translate([0,0,BAR_Z]) bar(); deck_pose() deck(); }
module bolt_envelope(x,z,y0,y1) {
    // Shaft D6, external washer OD12/t1.6, head/nut envelopes; no thread mesh.
    // Only the contact faces of CSG gauges are inset; shaft/radial sizes unchanged.
    g = PART=="collision_hardware" ? GAUGE_EPS : 0;
    translate([x,y0,z]) rotate([-90,0,0]) cylinder(h=y1-y0,d=6);
    translate([x,y0-1.6,z]) rotate([-90,0,0]) cylinder(h=1.6-g,d=12);
    translate([x,y1+g,z]) rotate([-90,0,0]) cylinder(h=1.6-g,d=12);
    translate([x,y1+1.6,z]) rotate([-90,0,0]) cylinder(h=6,d=10);
    translate([x,y0-8,z]) rotate([-90,0,0]) cylinder(h=6.4,d=12);
}
module hardware_envelopes() {
    for(side=[-1,1]) {
        for(z=[LOWER_Z,LOWER_Z+45]) bolt_envelope(side*POST_X,z,-14,18);
        for(z=[30,60]) bolt_envelope(side*POST_X,z,-14,10);
    }
    for(z=[LOWER_Z,LOWER_Z+45]) bolt_envelope(CAMERA_SLIDE,z,0,28);
}
module hardware_intersections() {
    // Distribute intersection across parts; avoid unioning a touching whole assembly.
    for(s=[-1,1]) {
        intersection() {
            translate([s*POST_X,0,RAIL_BOTTOM_Z]) rail();
            union() {
                for(z=[30,60]) bolt_envelope(s*POST_X,z,-14,10);
                for(z=[LOWER_Z,LOWER_Z+45]) bolt_envelope(s*POST_X,z,-14,18);
            }
        }
        intersection() {
            translate([s*POST_X,0,0]) scale([s,1,1]) base();
            union() for(z=[30,60]) bolt_envelope(s*POST_X,z,-14,10);
        }
    }
    intersection() { translate([0,0,BAR_Z]) bar(); hardware_envelopes(); }
    intersection() { deck_pose() deck(); hardware_envelopes(); }
}
module assembly() {
    color([0.75,0.76,0.78,0.3]) translate([-210,-55,-3]) cube([420,CAMERA_Y+310,3]);
    color([0.55,0.58,0.6,0.6]) conveyor();
    color("SeaGreen") translate([-BELT_WIDTH/2,CAMERA_Y-CONVEYOR_LENGTH/2,CONVEYOR_BOTTOM_Z+CONVEYOR_SIDE_HEIGHT]) cube([BELT_WIDTH,CONVEYOR_LENGTH,0.2]);
    color([1,0.1,0.8,0.6]) translate([-INSPECTION_ZONE_W/2,CAMERA_Y-INSPECTION_ZONE_L/2,CONVEYOR_BOTTOM_Z+CONVEYOR_SIDE_HEIGHT+0.3])
        cube([INSPECTION_ZONE_W,INSPECTION_ZONE_L,0.2]);
    color("DimGray") motor_ref();
    color("SteelBlue") bases();
    for(s=[-1,1]) {
        color("SteelBlue") translate([s*POST_X,0,10]) rail();
    }
    color("Orange") translate([0,0,BAR_Z]) bar();
    color("DarkOrange") deck_pose() deck();
    color([0.12,0.13,0.15]) deck_pose() body();
    color("Silver") deck_pose() lens();
    color("Purple") deck_pose() cable();
    color("Purple") cable_tail();
    color("DarkSlateGray") deck_pose() strap();
    color([0.5,0.5,0.5,0.6]) hardware_envelopes();
    color("Gray") table_fasteners();
    if(SHOW_FOV) color([0.05,0.75,0.85,0.18]) camera_fov_reference();
    color("Crimson") deck_pose() translate([LENS_OFFSET_X,CAMERA_Y+LENS_OFFSET_Y,BODY_Z-55]) {
        cylinder(h=40,r=1.4); translate([0,0,-9]) cylinder(h=9,r1=0,r2=5);
    }
}

// Print transforms are also inverted by the mesh validation tool.
if(PART=="base_right") translate([UPRIGHT_WIDTH/2,40,0]) base();
else if(PART=="base_left") translate([BASE_W-UPRIGHT_WIDTH/2,40,0]) mirror([1,0,0]) base();
else if(PART=="upright_300") translate([UPRIGHT_WIDTH/2,RAIL_LENGTH,UPRIGHT_THICKNESS]) rotate([90,0,0]) rail();
else if(PART=="upright_hole_coupon") translate([UPRIGHT_WIDTH/2,65,UPRIGHT_THICKNESS]) rotate([90,0,0]) rail(true);
else if(PART=="crossbar") translate([BAR_LENGTH/2,BAR_H,0]) rotate([90,0,0]) bar();
else if(PART=="camera_deck") multmatrix([[0,1,0,-BAR_T],[0,0,1,0],[1,0,0,DECK_W/2],[0,0,0,1]]) deck();
else if(PART=="camera_deck_fit_coupon") translate([DECK_W/2,-COUPON_START_Y,-DECK_BOTTOM_Z]) deck(true);
else if(PART=="base_mount_coupon") base_coupon();
else if(PART=="camera_body_reference") body();
else if(PART=="conveyor_reference") conveyor();
else if(PART=="motor_reference") motor_ref();
else if(PART=="cable_reference") cable();
else if(PART=="cable_tail_reference") cable_tail();
else if(PART=="strap_reference") strap();
else if(PART=="hardware_reference") hardware_envelopes();
else if(PART=="rail_fasteners_reference")
    for(s=[-1,1],z=[BAR_BOLT_Z,BAR_BOLT_Z+45]) bolt_envelope(s*POST_X,z,-14,18);
else if(PART=="deck_fasteners_reference")
    for(z=[BAR_BOLT_Z,BAR_BOLT_Z+45]) bolt_envelope(0,z,0,28);
else if(PART=="base_fasteners_reference")
    for(s=[-1,1],z=[30,60]) bolt_envelope(s*POST_X,z,-14,10);
else if(PART=="table_fasteners_reference") table_fasteners();
else if(PART=="fov_reference") camera_fov_reference();
else if(PART=="collision_conveyor") intersection() { structure(); conveyor(); }
else if(PART=="collision_motor") intersection() { structure(); motor_ref(); }
else if(PART=="collision_rail_bar") intersection() { rails(); translate([0,0,BAR_Z]) bar(); }
else if(PART=="collision_deck_bar") intersection() { deck(); bar(); }
else if(PART=="collision_body_deck") intersection() { deck(); body(GAUGE_EPS); }
else if(PART=="collision_lens") intersection() { deck(); lens(); }
else if(PART=="collision_cable") intersection() { structure(); deck_pose() cable(); }
else if(PART=="collision_base_rail") intersection() {
    base(); translate([0,-GAUGE_EPS,RAIL_BOTTOM_Z+GAUGE_EPS]) rail();
}
else if(PART=="collision_hardware") hardware_intersections();
else if(PART=="collision_optical_deck") intersection() { deck_pose() deck(); camera_fov_reference(); }
else if(PART=="assembly") assembly();
else assert(false,"Unknown PART");
