package com.ansub.tvhome;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RectF;
import android.graphics.drawable.Drawable;

// Tiny white outline icons on a 24x24 grid, so the app needs no image resources.
// Each icon is a list of ops: 0=moveTo x y, 1=lineTo x y, 2=close, 3=circle cx cy r,
// 4=arc cx cy r startDegrees sweepDegrees (0 degrees is 3 o'clock, going clockwise),
// 5=the same arc joined to the current point.
final class LineIcon extends Drawable {
    static final int[] PLAY = {0, 60, 45, 1, 60, 195, 1, 190, 120, 2};
    static final int[] HDMI = {0, 30, 90, 1, 210, 90, 1, 210, 130, 1, 185, 160, 1, 55, 160, 1, 30, 130, 2,
            0, 80, 120, 1, 160, 120};
    static final int[] SETTINGS = {0, 40, 70, 1, 140, 70, 0, 180, 70, 1, 200, 70, 0, 40, 170, 1, 60, 170,
            0, 100, 170, 1, 200, 170, 3, 160, 70, 20, 3, 80, 170, 20};
    static final int[] PLUS = {0, 120, 50, 1, 120, 190, 0, 50, 120, 1, 190, 120};
    static final int[] WIFI = {4, 120, 195, 135, 225, 90, 4, 120, 195, 92, 225, 90, 4, 120, 195, 50, 225, 90,
            3, 120, 195, 4};
    static final int[] WIFI_2 = {4, 120, 195, 92, 225, 90, 4, 120, 195, 50, 225, 90, 3, 120, 195, 4};
    static final int[] WIFI_1 = {4, 120, 195, 50, 225, 90, 3, 120, 195, 4};
    static final int[] SLASH = {0, 50, 45, 1, 190, 205};
    static final int[] BLUETOOTH = {0, 70, 80, 1, 170, 160, 1, 120, 205, 1, 120, 35, 1, 170, 80, 1, 70, 160};
    static final int[] SOUND = {0, 35, 95, 1, 75, 95, 1, 120, 55, 1, 120, 185, 1, 75, 145, 1, 35, 145, 2,
            4, 120, 120, 40, -45, 90, 4, 120, 120, 78, -45, 90};
    static final int[] ETHERNET = {0, 40, 60, 1, 200, 60, 1, 200, 165, 1, 160, 165, 1, 160, 195, 1, 80, 195,
            1, 80, 165, 1, 40, 165, 2, 0, 85, 60, 1, 85, 100, 0, 120, 60, 1, 120, 100, 0, 155, 60, 1, 155, 100};
    static final int[] PICTURE ={0, 30, 50, 1, 210, 50, 1, 210, 165, 1, 30, 165, 2, 0, 120, 165, 1, 120, 200,
            0, 80, 200, 1, 160, 200};

    static final int[] SEARCH = {3, 105, 105, 62, 0, 150, 150, 1, 205, 205};
    static final int[] GEAR = {3, 120, 120, 34, 3, 120, 120, 70, 0, 190, 120, 1, 215, 120, 0, 170, 170, 1, 187, 187,
            0, 120, 190, 1, 120, 215, 0, 70, 170, 1, 53, 187, 0, 50, 120, 1, 25, 120, 0, 70, 70, 1, 53, 53,
            0, 120, 50, 1, 120, 25, 0, 170, 70, 1, 187, 53};
    static final int[] GRID = {0, 40, 40, 1, 105, 40, 1, 105, 105, 1, 40, 105, 2, 0, 135, 40, 1, 200, 40, 1, 200, 105,
            1, 135, 105, 2, 0, 40, 135, 1, 105, 135, 1, 105, 200, 1, 40, 200, 2, 0, 135, 135, 1, 200, 135,
            1, 200, 200, 1, 135, 200, 2};
    static final int[] GAMEPAD = {0, 78, 68, 1, 162, 68, 5, 162, 108, 40, -90, 90, 1, 216, 178, 5, 188, 178, 28, 0, 150,
            1, 148, 158, 1, 92, 158, 1, 76, 192, 5, 52, 178, 28, 30, 150, 1, 38, 108, 5, 78, 108, 40, 180, 90, 2,
            0, 76, 98, 1, 76, 130, 0, 60, 114, 1, 92, 114, 3, 150, 102, 6, 3, 178, 126, 6};

    private final int[] ops;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Path path = new Path();
    private final RectF arc = new RectF();

    LineIcon(int[] ops) {
        this.ops = ops;
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeCap(Paint.Cap.ROUND);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setColor(0xEBFFFFFF);
    }

    @Override
    public void draw(Canvas c) {
        if (ops == null) return;
        float s = getBounds().width() / 240f; // ops are in tenths of the 24-unit grid
        paint.setStrokeWidth(16 * s);
        path.reset();
        for (int i = 0; i < ops.length; ) {
            switch (ops[i]) {
                case 0: path.moveTo(ops[i + 1] * s, ops[i + 2] * s); i += 3; break;
                case 1: path.lineTo(ops[i + 1] * s, ops[i + 2] * s); i += 3; break;
                case 2: path.close(); i += 1; break;
                case 3: path.addCircle(ops[i + 1] * s, ops[i + 2] * s, ops[i + 3] * s, Path.Direction.CW); i += 4; break;
                default:
                    float cx = ops[i + 1] * s, cy = ops[i + 2] * s, r = ops[i + 3] * s;
                    arc.set(cx - r, cy - r, cx + r, cy + r);
                    if (ops[i] == 4) path.addArc(arc, ops[i + 4], ops[i + 5]);
                    else path.arcTo(arc, ops[i + 4], ops[i + 5], false);
                    i += 6;
            }
        }
        c.save();
        c.translate(getBounds().left, getBounds().top);
        c.drawPath(path, paint);
        c.restore();
    }

    @Override public void setAlpha(int a) { paint.setAlpha(a); }
    @Override public void setColorFilter(ColorFilter cf) { paint.setColorFilter(cf); }
    @Override public int getOpacity() { return PixelFormat.TRANSLUCENT; }
    @Override public int getIntrinsicWidth() { return 44; }
    @Override public int getIntrinsicHeight() { return 44; }
}
