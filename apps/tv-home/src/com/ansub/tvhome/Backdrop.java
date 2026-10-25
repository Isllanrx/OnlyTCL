package com.ansub.tvhome;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.LinearGradient;
import android.graphics.Shader;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.Drawable;
import android.graphics.drawable.LayerDrawable;
import android.graphics.drawable.ShapeDrawable;
import android.graphics.drawable.shapes.RectShape;
import android.util.Log;

import java.io.InputStream;

final class Backdrop {

    static final String[] PHOTOS = {"everest.jpg", "lake.jpg"};
    static final int[][] DOTS = {
        {0xFF2A2350, 0xFF14112A, 0xFF0A0812, 0xC0FF5A2A, 0x80B8C8E0},
        {0xFF6A4A26, 0xFF2E2014, 0xFF0E0A08, 0xC0FFB860, 0x80C08040},
    };
    private static final int BASE = 0xFF0B0910;
    private static int request;

    static void show(final Activity a, final int i) {
        final int ticket = ++request;
        a.getWindow().setBackgroundDrawable(new ColorDrawable(BASE));
        new Thread(() -> {
            final Bitmap bmp = decode(a, PHOTOS[i]);
            if (bmp == null) return;
            a.runOnUiThread(() -> {
                if (ticket != request || a.isFinishing()) return;
                BitmapDrawable photo = new BitmapDrawable(a.getResources(), bmp);
                photo.setFilterBitmap(true);
                a.getWindow().setBackgroundDrawable(new LayerDrawable(new Drawable[] {photo, shade()}));
            });
        }, "backdrop").start();
    }

    static void cancel() {
        request++;
    }

    private static Bitmap decode(Activity a, String name) {
        try (InputStream in = a.getAssets().open(name)) {
            return BitmapFactory.decodeStream(in);
        } catch (Exception e) {
            Log.w("tvhome", "backdrop " + name, e);
            return null;
        }
    }

    private static Drawable shade() {
        ShapeDrawable d = new ShapeDrawable(new RectShape());
        d.setShaderFactory(new ShapeDrawable.ShaderFactory() {
            @Override
            public Shader resize(int w, int h) {
                return new LinearGradient(0, 0, 0, h,
                        new int[] {0x66000000, 0x14000000, 0x00000000, 0xB80B0910, 0xF00B0910},
                        new float[] {0f, 0.26f, 0.4f, 0.6f, 1f}, Shader.TileMode.CLAMP);
            }
        });
        d.setDither(true);
        return d;
    }
}
