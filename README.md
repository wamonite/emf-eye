# EMF Eye

```
usage: emf-eye [-h] [-f] [-i] [-s]

EMF eye renderer

options:
  -h, --help        show this help message and exit
  -f, --fullscreen  use the full screen (default: False)
  -i, --invert      invert horizontal coordinates (default: False)
  -s, --showreel    switch scene every 300 seconds (default: False)
```

When running on the projector, both `-f` and `-i` should be enabled.

Warp parameters can be edited with an attached Akai LPD8 controller with program 2 loaded with default values.

Keys:-

* left or right arrows to switch scenes
* `w`: Enable and disable the texture warp
* `m`: Enable changing the eye position with the mouse
* `h`: Show or hide the mouse pointer
* `p`: Show the warp points
* `l`: Load the warp parameters
* `s`: Save the current warp parameters
* `q`: Quit
