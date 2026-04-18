"""
pose_controller.py
------------------
Translates body pose into WASD keypresses.

  Lean left       → A
  Lean right      → D
  Arms out        → W
  Left Arm Up     → Space
  Squat           → S
"""

import sys, os, math, urllib.request
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from pynput.keyboard import Controller as Keyboard, Key

# ── Model download ───────────────────────────────────────────────────────────
MODEL_URL  = ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
              "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "pose_landmarker_heavy.task")

def ensure_model():
    if not os.path.isfile(MODEL_PATH):
        print("Downloading pose model (~26 MB)…")
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

# ── Landmark indices ─────────────────────────────────────────────────────────
L_SHOULDER, R_SHOULDER = 11, 12
L_HIP,      R_HIP      = 23, 24
L_KNEE,     R_KNEE     = 25, 26
L_ANKLE,    R_ANKLE    = 27, 28
L_WRIST,    R_WRIST    = 15, 16

# Bones to draw — pairs of landmark indices
SKELETON = [
    (11, 12),           # shoulders
    (11, 13), (13, 15), # left arm
    (12, 14), (14, 16), # right arm
    (11, 23), (12, 24), # torso sides
    (23, 24),           # hips
    (23, 25), (25, 27), # left leg
    (24, 26), (26, 28), # right leg
]

# ── Thresholds ───────────────────────────────────────────────────────────────
LEAN_THRESHOLD   = 0.045   # shoulder-hip horizontal offset
SQUAT_ANGLE      = 150.0   # knee angle below this = squat
ARMS_OUT_Y_TOL   = 0.08    # how level wrists must be vs shoulders
ARMS_OUT_X_SPAN  = 0.45    # min wrist-to-wrist width (normalised)
ARM_UP_THRESHOLD = 0.2     # wrist must be this far above shoulder
WRIST_THRESHOLD = 0.1
WRIST_RELEASE_THRESHOLD = 0.25

def knee_angle(hip, knee, ankle):
    """Angle at the knee in degrees."""
    a = (hip[0]-knee[0],   hip[1]-knee[1])
    b = (ankle[0]-knee[0], ankle[1]-knee[1])
    dot = a[0]*b[0] + a[1]*b[1]
    mag = math.hypot(*a) * math.hypot(*b)
    return math.degrees(math.acos(max(-1, min(1, dot/mag)))) if mag > 1e-8 else 180

def get_keys(lm):
    ls, rs = lm[L_SHOULDER], lm[R_SHOULDER]
    lh, rh = lm[L_HIP],      lm[R_HIP]
    lk, rk = lm[L_KNEE],     lm[R_KNEE]
    la, ra = lm[L_ANKLE],    lm[R_ANKLE]
    lw, rw = lm[L_WRIST],    lm[R_WRIST]

    keys = set()

    # W — arms stretched out to the sides
    if (abs(lw.y - ls.y) < ARMS_OUT_Y_TOL and
            abs(rw.y - rs.y) < ARMS_OUT_Y_TOL and
            abs(lw.x - rw.x) > ARMS_OUT_X_SPAN):
        keys.add('w')

    # A / D — lean left or right
    lean = (ls.x + rs.x)/2 - (lh.x + rh.x)/2
    if   lean >  LEAN_THRESHOLD: keys.add('d')
    elif lean < -LEAN_THRESHOLD: keys.add('a')

    # SPACE — left wrist above left shoulder
    if (ls.y - lw.y) > ARM_UP_THRESHOLD:
        keys.add(Key.space)

    # S — squat (both knees bent)
    angles = [
        knee_angle((lh.x,lh.y),(lk.x,lk.y),(la.x,la.y)),
        knee_angle((rh.x,rh.y),(rk.x,rk.y),(ra.x,ra.y)),
    ]
    if sum(angles)/len(angles) < SQUAT_ANGLE:
        keys.add('s')


    return keys

def draw_skeleton(frame, landmarks):
    """Draw bones and joint dots onto the frame."""
    h, w = frame.shape[:2]

    # convert normalised coords to pixel coords
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in landmarks]

    # bones
    for (a, b) in SKELETON:
        cv2.line(frame, pts[a], pts[b], (0, 255, 100), 2, cv2.LINE_AA)

    # joints
    for (x, y) in pts:
        cv2.circle(frame, (x, y), 4, (255, 255, 255), -1, cv2.LINE_AA)

def draw_hud(frame, keys):
    """Show active keys in the top-left corner."""
    parts = []
    for k in keys:
        parts.append("SPACE" if k == Key.space else str(k).upper())
    label = "  ".join(parts) if parts else "idle"
    cv2.putText(frame, label, (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 100), 2)

# ── Main loop ────────────────────────────────────────────────────────────────

def main():
    ensure_model()

    kb = Keyboard()
    held = set()

    opts = vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
    )
    landmarker = vision.PoseLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        sys.exit("Cannot open webcam")

    ts = 0
    print("Running — press Q in the camera window to quit")

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame = cv2.flip(frame, 1)
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ts   += 33

        result = landmarker.detect_for_video(
            mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), ts)

        wanted = set()
        if result.pose_landmarks:
            lm = result.pose_landmarks[0]
            wanted = get_keys(lm)
            draw_skeleton(frame, lm)

        # press / release only what changed
        for k in held - wanted:  kb.release(k)
        for k in wanted - held:  kb.press(k)
        held = wanted

        draw_hud(frame, held)
        cv2.imshow("Pose Controller", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    for k in held: kb.release(k)
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
