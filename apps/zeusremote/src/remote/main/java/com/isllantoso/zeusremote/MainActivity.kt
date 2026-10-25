package com.isllantoso.zeusremote

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.util.TypedValue
import android.view.Gravity
import android.widget.TextView

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        BridgeService.start(this)
        setContentView(TextView(this).apply {
            gravity = Gravity.CENTER
            setBackgroundColor(Color.BLACK)
            setTextColor(Color.WHITE)
            setTextSize(TypedValue.COMPLEX_UNIT_SP, 28f)
            text = BridgeService.controlUrl()?.let { getString(R.string.open_on_phone, it) } ?: getString(R.string.no_network)
        })
    }
}
