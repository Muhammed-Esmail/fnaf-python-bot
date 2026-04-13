import pyautogui as pg
import psutil
# from pynput import keyboard
import threading
import time
import os
from constants import COORDINATES # import the COORDINATES from the constants file

pg.PAUSE = 0.05

class GameState:
    # Define all the variables that will be used to track the state of the game
    def __init__(self):
        # Create a lock for thread safety
        self._lock = threading.Lock()
        
        self.facingRight = False
        self.cameraUp = False
        self.lightOn = False
        self.leftDoorClosed = False
        self.rightDoorClosed = False
        self.robotAtDoor = False
        self.foxyCheck = 0
        self.onTitle = False
        self.star1 = False
        self.star2 = False
        self.star3 = False
        self.inOffice = False


    # Getter for any attribute
    def get(self, attr):
        with self._lock:
            return getattr(self, attr)
        
    # Setter for any attribute
    def set(self, attr, value):
        with self._lock:
            return setattr(self, attr, value)

state = GameState()

class TimeoutError(Exception):
    pass

class StateCaptureError(Exception):
    pass

# Monkey patch for pyautogui's "pixelMatchesColor" function
def customPMC(x=0, y=0, expectedRGBColor=(0, 0, 0), tolerance=0, sample=None):
    if isinstance(x, pg.collections.abc.Sequence) and len(x) == 2:
        raise TypeError('pixelMatchesColor() has updated and no longer accepts a tuple of (x, y) values for the first argument. Pass these arguments as two separate arguments instead: pixelMatchesColor(x, y, rgb) instead of pixelMatchesColor((x, y), rgb)')

    pix = pg.pixel(x, y) if sample == None else sample
    if len(pix) == 3 or len(expectedRGBColor) == 3:  # RGB mode
        r, g, b = pix[:3]
        exR, exG, exB = expectedRGBColor[:3]
        return (abs(r - exR) <= tolerance) and (abs(g - exG) <= tolerance) and (abs(b - exB) <= tolerance)
    elif len(pix) == 4 and len(expectedRGBColor) == 4:  # RGBA mode
        r, g, b, a = pix
        exR, exG, exB, exA = expectedRGBColor
        return (
            (abs(r - exR) <= tolerance)
            and (abs(g - exG) <= tolerance)
            and (abs(b - exB) <= tolerance)
            and (abs(a - exA) <= tolerance)
        )
    else:
        assert False, (
            'Color mode was expected to be length 3 (RGB) or 4 (RGBA), but pixel is length %s and expectedRGBColor is length %s'  # noqa
            % (len(pix), len(expectedRGBColor))
        )
pg.pixelMatchesColor = customPMC

def toggleButton(button):
    moveMouse(COORDINATES[button])
    if "left" in button:
        waitUntil(isNotFacingRight, 5.0)
    if "right" in button:
        waitUntil(isFacingRight, 5.0)
    clickMouse()

def toggleCamera():
    moveMouse((0.43072916666666666, 0.98))
    time.sleep(0.1)
    moveMouse((0.43072916666666666, 0.85))

def camera(cam):
    moveMouse(COORDINATES[cam])
    clickMouse()

# Functions for detecting states
def isCamUp():
    return state.get("cameraUp")
def isFacingRight():
    return state.get("facingRight")
def isNotFacingRight():
    return not isFacingRight()


# Controls the night gameplay
def officeLoop():

    # Initialize variables
    state.set("foxyCheck", 0)
    state.set("leftDoorClosed", False)
    state.set("rightDoorClosed", False)

    # East hall corner at the start of the night
    toggleCamera()
    waitUntil(isCamUp, 5.0)
    camera("hallCorner")
    time.sleep(0.01)
    toggleCamera()
    try:
        while True:
            # Check left light
            lightCheck("leftLight")

            # Toggle door accordingly
            if state.get("robotAtDoor") and not state.get("leftDoorClosed"):
                state.set("leftDoorClosed", True)
                toggleButton("leftDoor")
            elif state.get("leftDoorClosed") and not state.get("robotAtDoor"):
                state.set("leftDoorClosed", False)
                toggleButton("leftDoor")
            state.set("robotAtDoor", False)

            # Flip camera
            camFlip()

            # If haven't checked foxy in a while, then do that instead of checking Chica
            if state.get("foxyCheck") >= 50:
                if not state.get("rightDoorClosed"):
                    state.set("rightDoorClosed", True)
                    toggleButton("rightDoor")
                else:
                    time.sleep(0.5)
                checkFoxy()
            else:
                checkChica()

                # Flip camera or check Foxy
                if state.get("foxyCheck") >= 40 and state.get("rightDoorClosed"):
                    checkFoxy()
                else:
                    camFlip()

            time.sleep(0.01)
    except TimeoutError as e:
        print(f"Office loop timed out: {e}")

def camFlip():
    toggleCamera()
    waitUntil(isCamUp, 5.0)
    state.set("foxyCheck", state.get("foxyCheck") + 1)
    toggleCamera()

def lightCheck(light):
    toggleButton(light)
    state.set("lightOn", True)
    moveMouse((COORDINATES[light][0] + 0.01, COORDINATES[light][1]))
    time.sleep(0.15)
    clickMouse()
    state.set("lightOn", False)

def checkFoxy():
    state.set("foxyCheck", 0)

    # Open camera and wait for it to open
    toggleCamera()
    waitUntil(isCamUp, 5.0)
    # Switch to the west hall briefly to make Foxy run if he's there
    camera("westHall")
    time.sleep(0.05)
    camera("hallCorner")
    time.sleep(0.05)
    # Close the camera
    toggleCamera()
    # Close the left door
    if not state.get("leftDoorClosed"):
        state.set("leftDoorClosed", True)
        toggleButton("leftDoor")
    else:
        time.sleep(0.5)
    # Continue game loop starting with checking Chica
    checkChica()
    camFlip()

def checkChica():
    # Check right light
    lightCheck("rightLight")

    # Toggle door accordingly
    if state.get("robotAtDoor") and not state.get("rightDoorClosed"):
        state.set("rightDoorClosed", True)
        toggleButton("rightDoor")
    elif state.get("rightDoorClosed") and not state.get("robotAtDoor"):
        state.set("rightDoorClosed", False)
        toggleButton("rightDoor")
    state.set("robotAtDoor", False)

def moveMouse(coords):
    pg.moveTo(
            coords[0] * pg.size()[0],
            coords[1] * pg.size()[1]
        )

def clickMouse():
    pg.mouseDown()
    time.sleep(0.02)
    pg.mouseUp()
    time.sleep(0.02)

def getPosition():
    width, height = pg.size()
    return (pg.position().x / width, pg.position().y / height)

def getPixel(coords, sc):
    width, height = sc.size
    return sc.getpixel((int(COORDINATES[coords][0] * width), int(COORDINATES[coords][1] * height)))

def detectStars():
    if not state.get("star1"): return 0
    if not state.get("star2"): return 1
    if not state.get("star3"): return 2
    return 3

def waitUntil(condition, maxTime):
    endTime = time.time() + maxTime
    while not condition():
        time.sleep(0.01)
        if time.time() >= endTime:
            raise TimeoutError(f"Timed out waiting for {condition.__name__}")

# This controls the flow of the game
def gameLoop():
    # Wait for the title screen
    while True:
        while True:
            time.sleep(1.0)
            if state.get("onTitle") or state.get("inOffice"): break

        if state.get("onTitle") and not state.get("inOffice"):
            # Detect how many stars there are
            stars = detectStars()
            match stars:
                case 0:
                    moveMouse(COORDINATES["continue"])
                case 1:
                    moveMouse(COORDINATES["sixthNight"])
                case 2:
                    moveMouse(COORDINATES["customNight"])
                    # Set the mode to 20/20/20/20
                    clickMouse()
                    time.sleep(3.0)
                    for i in range(4):
                        moveMouse(COORDINATES[["freddyArrow","bonnieArrow","chicaArrow","foxyArrow"][i]])
                        for _ in range([19, 17, 17, 19][i]):
                            time.sleep(1.0)
                            clickMouse()
                    moveMouse(COORDINATES["ready"])
                case 3:
                    os._exit(1)
            clickMouse()
            time.sleep(1.0)
            state.set("onTitle", False)

        if state.get("inOffice"):
            # Start office loop after 3 seconds
            time.sleep(3.0)
            officeLoop()
            time.sleep(1.0)
            state.set("inOffice", False)
    

# This loop is for checking states of the game and setting variables
def detectStates():
    while True:
        # Getting a screenshot instead of calling pixel()
        # Without try it could throw a KeyboardInterrupt error
        screenshot = None

        try:
            screenshot = pg.screenshot()
        except Exception as e:
            print(f"Error taking screenshot: {e}")


        try:
            if screenshot:
                # If left door button in frame, then facing left
                pixelCheck = getPixel("leftDoor", screenshot)
                if pg.pixelMatchesColor(expectedRGBColor=(109, 0, 0), sample=pixelCheck, tolerance=50):
                    state.set("facingRight", False)
                if pg.pixelMatchesColor(expectedRGBColor=(29, 107, 0), sample=pixelCheck, tolerance=80):
                    state.set("facingRight", False)

                # If right door button in frame, then facing right
                pixelCheck = getPixel("rightDoor", screenshot)
                if pg.pixelMatchesColor(expectedRGBColor=(163, 0, 0), sample=pixelCheck, tolerance=50):
                    state.set("facingRight", True)
                if pg.pixelMatchesColor(expectedRGBColor=(35, 128, 0), sample=pixelCheck, tolerance=80):
                    state.set("facingRight", True)

                # If restroom button in frame, then camera is open
                pixelCheck = getPixel("cameraCheck", screenshot)
                state.set("cameraUp", pg.pixelMatchesColor(expectedRGBColor=(66, 66, 66), sample=pixelCheck, tolerance=2))

                # Detect animatronics at the door
                if state.get("lightOn"):
                    if state.get("facingRight"):
                        pixelCheck = getPixel("chicaCheck", screenshot)
                        if pg.pixelMatchesColor(expectedRGBColor=(86, 95, 9), sample=pixelCheck, tolerance=20):
                            state.set("robotAtDoor", True)
                    else: # Facing left
                        # If door closed, check for Bonnie's shadow
                        if state.get("leftDoorClosed"):
                            bonniePixel1 = getPixel("bonnieCheck1", screenshot)
                            bonniePixel2 = getPixel("bonnieCheck2", screenshot)
                            if pg.pixelMatchesColor(expectedRGBColor=(0, 0, 0), sample=bonniePixel1) and\
                                pg.pixelMatchesColor(expectedRGBColor=(30, 42, 65), sample=bonniePixel2, tolerance=5):
                                state.set("robotAtDoor", True)
                        else:
                            pixelCheck = getPixel("bonnieCheckDoor", screenshot)
                            if pg.pixelMatchesColor(expectedRGBColor=(54, 37, 63), sample=pixelCheck, tolerance=10):
                                state.set("robotAtDoor", True)
                
                # Detect if you're on the title screen
                pixelCheck = getPixel("titleCheck", screenshot)
                state.set("onTitle", pg.pixelMatchesColor(expectedRGBColor=(255, 255, 255), sample=pixelCheck))

                # Detect the stars on the menu
                pixelCheck = getPixel("star1", screenshot)
                state.set("star1", pg.pixelMatchesColor(expectedRGBColor=(255, 255, 255), sample=pixelCheck))
                if state.get("star1"):
                    pixelCheck = getPixel("star2", screenshot)
                    state.set("star2", pg.pixelMatchesColor(expectedRGBColor=(255, 255, 255), sample=pixelCheck))
                if state.get("star2"):
                    pixelCheck = getPixel("star3", screenshot)
                    state.set("star3", pg.pixelMatchesColor(expectedRGBColor=(255, 255, 255), sample=pixelCheck))

                # Detect if inside the office
                pixelCheck = getPixel("officeCheck", screenshot)
                state.set("inOffice", pg.pixelMatchesColor(expectedRGBColor=(35, 235, 31), sample=pixelCheck, tolerance=5))
            
        except Exception as e:
            raise StateCaptureError(f"Error capturing game state at {e}")

        time.sleep(0.05)

if __name__ == "__main__":
    # listener = keyboard.Listener(on_press = onPress)
    # listener.start()

    print("Program started! Waiting for game to open...")

    # Wait for the game to open before starting anything
    def isRunning(name):
        print("Checking if process is running...")
        for i in psutil.process_iter(["name"]):
            if i.info["name"] == name:
                return True
        return False

    while True:
        time.sleep(2.0)
        if isRunning("FiveNightsatFreddys.exe"):
            print("Game detected! Starting bot...")
            break

    # Wait 5 seconds to make sure the game is open in fullscreen
    
    time.sleep(1.0)
    moveMouse((0.6, 0.6))

    gameloopProcess = threading.Thread(target=gameLoop, daemon=True) # daemon kills it when the main thread exits
    detectProcess = threading.Thread(target=detectStates, daemon=True)
    gameloopProcess.start()
    detectProcess.start()

    # If one of them dies, the main thread also dies
    gameloopProcess.join()
    detectProcess.join()