package com.ansub.tvhome;

import android.graphics.Canvas;
import android.graphics.ColorFilter;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.PixelFormat;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.Shader;
import android.graphics.drawable.Drawable;

import java.util.Random;

final class MountainDrawable extends Drawable {

    static final int[] PALETTE = {0xFF3A1A12, 0xFF1C0F0D, 0xFF0E0909, 0x80FF7A2E, 0x50B8341E};

    private static final int SEGMENTS = 128;
    private static final float SUN_X = 0.63f, SUN_Y = 0.30f;

    private static final int[][] LAYERS = {
        {0xFF8A3E26, 0xFF5E2A1C, 33, 16, 7, 0x38FF9A58},
        {0xFF6A2C1C, 0xFF421D15, 38, 16, 13, 0x28FF8A48},
        {0xFF4A1E14, 0xFF2C130E, 44, 14, 29, 0x1CFF7C3C},
        {0xFF32150F, 0xFF1E0E0B, 50, 12, 41, 0x14FF7434},
        {0xFF20100C, 0xFF140A09, 56, 10, 53, 0x0CFF6C2C},
        {0xFF150B09, 0xFF0E0707, 62, 8, 67, 0x08FF6828},
    };

    private final Paint sky = new Paint(Paint.DITHER_FLAG);
    private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.DITHER_FLAG);
    private final Paint disc = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.DITHER_FLAG);
    private final Paint shade = new Paint(Paint.DITHER_FLAG);
    private final Path[] bodies = new Path[LAYERS.length];
    private final Path[] crests = new Path[LAYERS.length];
    private final Paint[] fills = new Paint[LAYERS.length];
    private final Paint[] lights = new Paint[LAYERS.length];
    private final Paint[] rims = new Paint[LAYERS.length];
    private final Paint[] mists = new Paint[LAYERS.length];

    @Override
    protected void onBoundsChange(Rect b) {
        int w = b.width(), h = b.height();
        if (w == 0 || h == 0) return;
        float sx = w * SUN_X, sy = h * SUN_Y;
        sky.setShader(new LinearGradient(0, 0, 0, h * 0.46f,
                new int[] {0xFF1C0D14, 0xFF4E1C1A, 0xFFB44A28, 0xFFF0883C, 0xFFF6A050},
                new float[] {0f, 0.3f, 0.65f, 0.9f, 1f}, Shader.TileMode.CLAMP));
        glow.setShader(new RadialGradient(sx, sy, w * 0.45f,
                new int[] {0xC0FFB060, 0x50F06A28, 0x00E05A20}, new float[] {0f, 0.35f, 1f}, Shader.TileMode.CLAMP));
        float r = w * 0.032f;
        disc.setShader(new RadialGradient(sx, sy, r,
                new int[] {0xFFFFF0C8, 0xFFFFD088, 0x00FFC070}, new float[] {0f, 0.75f, 1f}, Shader.TileMode.CLAMP));
        for (int i = 0; i < LAYERS.length; i++) {
            int[] l = LAYERS[i];
            float base = h * l[2] / 100f, amp = h * l[3] / 100f;
            float[] y = ridge(base, amp, l[4]);
            bodies[i] = body(w, h, y);
            crests[i] = crest(w, y);
            fills[i] = paint(new LinearGradient(0, base - amp, 0, base + h * 0.12f, l[0], l[1], Shader.TileMode.CLAMP));
            lights[i] = paint(new RadialGradient(sx, sy, w * 0.5f, l[5], l[5] & 0x00FFFFFF, Shader.TileMode.CLAMP));
            Paint rim = paint(new RadialGradient(sx, sy, w * 0.42f, 0x90FFB070, 0x00FFB070, Shader.TileMode.CLAMP));
            rim.setStyle(Paint.Style.STROKE);
            rim.setStrokeWidth(Math.max(1.5f, w / 900f));
            rim.setStrokeJoin(Paint.Join.ROUND);
            rims[i] = rim;
            mists[i] = paint(new LinearGradient(0, base - amp * 0.3f, 0, base + h * 0.07f,
                    new int[] {0x00D8703C, 0x1CD8703C, 0x00D8703C}, null, Shader.TileMode.CLAMP));
        }
        shade.setShader(new LinearGradient(0, h * 0.44f, 0, h,
                new int[] {0x00120B0B, 0xE6120B0B, 0xFF120B0B}, new float[] {0f, 0.35f, 1f}, Shader.TileMode.CLAMP));
    }

    private static Paint paint(Shader s) {
        Paint p = new Paint(Paint.ANTI_ALIAS_FLAG | Paint.DITHER_FLAG);
        p.setShader(s);
        return p;
    }

    private static float[] ridge(float base, float amp, int seed) {
        Random rnd = new Random(seed);
        float[] v = new float[SEGMENTS + 1];
        v[0] = rnd.nextFloat();
        v[SEGMENTS] = rnd.nextFloat();
        float range = 1.1f;
        for (int step = SEGMENTS; step > 1; step /= 2, range *= 0.47f) {
            for (int i = step / 2; i < SEGMENTS; i += step) {
                v[i] = (v[i - step / 2] + v[i + step / 2]) / 2 + (rnd.nextFloat() - 0.5f) * range;
            }
        }
        float min = Float.MAX_VALUE, max = -Float.MAX_VALUE;
        for (float f : v) { min = Math.min(min, f); max = Math.max(max, f); }
        float[] y = new float[SEGMENTS + 1];
        for (int i = 0; i <= SEGMENTS; i++) y[i] = base - amp * (v[i] - min) / (max - min);
        return y;
    }

    private static Path body(int w, int h, float[] y) {
        Path p = new Path();
        p.moveTo(0, h);
        for (int i = 0; i <= SEGMENTS; i++) p.lineTo(w * i / (float) SEGMENTS, y[i]);
        p.lineTo(w, h);
        p.close();
        return p;
    }

    private static Path crest(int w, float[] y) {
        Path p = new Path();
        p.moveTo(0, y[0]);
        for (int i = 1; i <= SEGMENTS; i++) p.lineTo(w * i / (float) SEGMENTS, y[i]);
        return p;
    }

    @Override
    public void draw(Canvas c) {
        Rect b = getBounds();
        c.drawRect(b, sky);
        c.drawRect(b, glow);
        c.drawRect(b, disc);
        for (int i = 0; i < bodies.length; i++) {
            if (bodies[i] == null) continue;
            c.drawPath(bodies[i], fills[i]);
            c.drawPath(bodies[i], lights[i]);
            c.drawPath(crests[i], rims[i]);
            c.drawRect(b, mists[i]);
        }
        c.drawRect(b, shade);
    }

    @Override public void setAlpha(int a) {}
    @Override public void setColorFilter(ColorFilter cf) {}
    @Override public int getOpacity() { return PixelFormat.OPAQUE; }
}
