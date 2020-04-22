# Ten Mile Square g2core Pressurizer Bill-of-Materials

This is the parts list we used to build our proof of concept, and unless otherwise noted the parts can be replaced by similar:

## Mechanical

- [OpenBuilds C-Beam® Linear Actuator Bundle](https://openbuildspartstore.com/c-beam-linear-actuator-bundle/) - 250mm version
  - [Add the High-Torque NEMA-23 Motor](https://openbuildspartstore.com/nema-23-stepper-motor-high-torque-series/) - the normal NEMA-23 _might_ work but our testing shows that we're near the torque limit of this motor
- [OpenBuilds V-Slot® 20x80 Linear Rail](https://openbuildspartstore.com/v-slot-20x80-linear-rail/) - at _least_ 250mm length - will be cut into two
- Corner brackets - at _least_ 6 - [Angle Corner Connector](https://openbuildspartstore.com/black-angle-corner-connector/) (Needs tested: may be able to only use 4 total for cost reduction)
  - To save money, *at most two of them* may be able to be replaced with these [cast version](https://openbuildspartstore.com/cast-corner-bracket/) *or* [these hidden ones](https://openbuildspartstore.com/inside-hidden-corner-bracket/)
- 1 x [Tee Nuts - M5 (10 Pack)](https://openbuildspartstore.com/tee-nuts-m5-10-pack/) - only two are needed, but they're sold in 10-packs
- 1 x *8mm* [Low Profile Screws M5 (10 Pack)
](https://openbuildspartstore.com/low-profile-screws-m5-10-pack/) - only 4 are needed, but they're sold in 10 packs
  - You *may* use other head shaped M5 screws but the length is important - if they're too long, you may need to add washers to make it work
- 1 x *15mm* [Low Profile Screws M5 (10 Pack)
](https://openbuildspartstore.com/low-profile-screws-m5-10-pack/) (Note: Same link as the previous item, you mush choose a different size) - only 2 are needed, but they're sold in 10 packs
  - These two *must* be these low-profile kind, as they're placed so the head has to fit *under* the gantry plate without hitting the C-Beam
  - It might be possible to omit these - testing is needed
- *Optional* 2 x [Handles](https://openbuildspartstore.com/v-slot-door-handle/) - comes with the nusts and screws needed
- *Optional* Some thin (roughly 1/8" or 3mm) foam or cloth to protect the BVM from the sharp edges
- *Optional* Some tape or cloth to hold the bag in place and up from getting pinched in machinery
- 1 x Limit switch - [Option 1](https://openbuildspartstore.com/xtension-limit-switch-kit/), [Option 2](https://openbuildspartstore.com/micro-limit-switch-kit/), [Option 3 -  requires finding a means of attaching it](https://openbuildspartstore.com/micro-limit-switch/)

## Electrical

- Power supply - 12V or 24V power supply - *Add Links to OpenBuilds and Adafruit*
- Stepper motor driver - There are many many options. Here's the one we used: [STR3 from Applied Motion](https://www.applied-motion.com/products/STR3-miniature-advanced-microstep-drive). Here's a nice one from [OMC StepperOnline](https://www.omc-stepperonline.com/digital-stepper-driver-10-42a-20-50vdc-for-nema-17-23-24-stepper-motor-dm542t.html).
  - Notes: You'll want current capability >2A peak per channel
  - It will need to take Step/Direction and (optionally) Enable signals.
- Controller board
  - Option 1: g2core gQuintic (currently prerelease) or g2core v9k (OEM edition) - as the gQuintic is not yet released and the v9k is only sold to OEM we recommend going with option two for now
  - Option 2: Arduino Due - [Arduino Store](https://store.arduino.cc/usa/due) - [SparkFun](https://www.sparkfun.com/products/11589)
    - Most of the stepper drivers will require 5V signals, so you'll need a voltage level shifter like [this one](https://www.adafruit.com/product/757) (more convenient) or [this one](https://www.adafruit.com/product/1787) (less convenient). In either case, you'll need basic soldering skillas and equipment in order to use them.
    - The Due can only handle power up to 12V before it starts to get uncomfortably hot. If you go with a 24V power supply you'll need to find some other means of safely powering the Due such as a separate power supply.
  
