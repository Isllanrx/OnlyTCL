package gamepass.fire.tv;

import android.app.Activity;
import android.hardware.input.InputManager;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.webkit.WebView;

public final class GamepadBridge {
    private static final int SCALE = 1000;
    private static final int STICK_DEADZONE = 80;
    private static final int TRIGGER_DEADZONE = 50;
    private static final int UP = 12;
    private static final int DOWN = 13;
    private static final int LEFT = 14;
    private static final int RIGHT = 15;

    private static final int[] axes = new int[4];
    private static final StringBuilder out = new StringBuilder(64);
    private static int buttons;
    private static int lt;
    private static int rt;
    private static int seq;
    private static boolean connected;
    private static volatile String state = "0,0";
    private static volatile boolean inGame;
    private static InputManager inputManager;

    private GamepadBridge() {}

    public static void attach(Activity activity, WebView webView) {
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);
        if (inputManager == null) {
            inputManager = activity.getSystemService(InputManager.class);
            inputManager.registerInputDeviceListener(new InputManager.InputDeviceListener() {
                @Override
                public void onInputDeviceAdded(int deviceId) {
                    refreshConnected();
                }

                @Override
                public void onInputDeviceRemoved(int deviceId) {
                    refreshConnected();
                }

                @Override
                public void onInputDeviceChanged(int deviceId) {
                    refreshConnected();
                }
            }, null);
        }
        refreshConnected();
    }

    public static void setInGame(boolean value) {
        inGame = value;
    }

    public static String state() {
        return state;
    }

    public static boolean onKeyEvent(KeyEvent event) {
        int index = buttonIndex(event.getKeyCode());
        if (index < 0 || !isGamepad(event.getSource())) return false;
        int action = event.getAction();
        if (action == KeyEvent.ACTION_DOWN || action == KeyEvent.ACTION_UP) {
            if (setButton(index, action == KeyEvent.ACTION_DOWN) || !connected) {
                connected = true;
                publish();
            }
        }
        return inGame;
    }

    public static boolean onGenericMotionEvent(MotionEvent event) {
        if (!isGamepad(event.getSource())) return false;
        int lx = stick(event.getAxisValue(MotionEvent.AXIS_X));
        int ly = stick(event.getAxisValue(MotionEvent.AXIS_Y));
        int rx = stick(event.getAxisValue(MotionEvent.AXIS_Z));
        int ry = stick(event.getAxisValue(MotionEvent.AXIS_RZ));
        int l = trigger(Math.max(event.getAxisValue(MotionEvent.AXIS_BRAKE), event.getAxisValue(MotionEvent.AXIS_LTRIGGER)));
        int r = trigger(Math.max(event.getAxisValue(MotionEvent.AXIS_GAS), event.getAxisValue(MotionEvent.AXIS_RTRIGGER)));
        float hatX = event.getAxisValue(MotionEvent.AXIS_HAT_X);
        float hatY = event.getAxisValue(MotionEvent.AXIS_HAT_Y);
        boolean changed = axes[0] != lx | axes[1] != ly | axes[2] != rx | axes[3] != ry | lt != l | rt != r;
        axes[0] = lx;
        axes[1] = ly;
        axes[2] = rx;
        axes[3] = ry;
        lt = l;
        rt = r;
        changed |= setButton(UP, hatY < -0.5f);
        changed |= setButton(DOWN, hatY > 0.5f);
        changed |= setButton(LEFT, hatX < -0.5f);
        changed |= setButton(RIGHT, hatX > 0.5f);
        if (changed || !connected) {
            connected = true;
            publish();
        }
        return inGame;
    }

    private static boolean isGamepad(int source) {
        return (source & InputDevice.SOURCE_GAMEPAD) == InputDevice.SOURCE_GAMEPAD
                || (source & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK;
    }

    private static void refreshConnected() {
        boolean found = false;
        for (int id : inputManager.getInputDeviceIds()) {
            InputDevice device = inputManager.getInputDevice(id);
            if (device != null && !device.isVirtual() && isGamepad(device.getSources())) {
                found = true;
                break;
            }
        }
        if (found == connected) return;
        connected = found;
        if (!found) {
            axes[0] = axes[1] = axes[2] = axes[3] = 0;
            buttons = lt = rt = 0;
        }
        publish();
    }

    private static int stick(float v) {
        int q = (int) (v * SCALE);
        return Math.abs(q) < STICK_DEADZONE ? 0 : q;
    }

    private static int trigger(float v) {
        int q = (int) (v * SCALE);
        return q < TRIGGER_DEADZONE ? 0 : q;
    }

    private static boolean setButton(int index, boolean pressed) {
        int next = pressed ? buttons | (1 << index) : buttons & ~(1 << index);
        if (next == buttons) return false;
        buttons = next;
        return true;
    }

    private static void publish() {
        StringBuilder sb = out;
        sb.setLength(0);
        sb.append(++seq).append(',').append(connected ? 1 : 0).append(',').append(buttons)
                .append(',').append(lt).append(',').append(rt);
        for (int a : axes) sb.append(',').append(a);
        state = sb.toString();
    }

    private static int buttonIndex(int keyCode) {
        switch (keyCode) {
            case KeyEvent.KEYCODE_BUTTON_A: return 0;
            case KeyEvent.KEYCODE_BUTTON_B: return 1;
            case KeyEvent.KEYCODE_BUTTON_X: return 2;
            case KeyEvent.KEYCODE_BUTTON_Y: return 3;
            case KeyEvent.KEYCODE_BUTTON_L1: return 4;
            case KeyEvent.KEYCODE_BUTTON_R1: return 5;
            case KeyEvent.KEYCODE_BUTTON_L2: return 6;
            case KeyEvent.KEYCODE_BUTTON_R2: return 7;
            case KeyEvent.KEYCODE_BUTTON_SELECT: return 8;
            case KeyEvent.KEYCODE_BUTTON_START: return 9;
            case KeyEvent.KEYCODE_BUTTON_THUMBL: return 10;
            case KeyEvent.KEYCODE_BUTTON_THUMBR: return 11;
            case KeyEvent.KEYCODE_DPAD_UP: return UP;
            case KeyEvent.KEYCODE_DPAD_DOWN: return DOWN;
            case KeyEvent.KEYCODE_DPAD_LEFT: return LEFT;
            case KeyEvent.KEYCODE_DPAD_RIGHT: return RIGHT;
            case KeyEvent.KEYCODE_BUTTON_MODE: return 16;
            default: return -1;
        }
    }
}
