from smooth_stream_dash import create_smooth_stream_app  # Imports the live dashboard

USE_REAL_ARDUINO = True  # Choose between real Arduino data and simulated data

if USE_REAL_ARDUINO:
    from arduino_accel_receiver import build_receiver  # If true, then use data from Arduino Cloud
else:
    from simulate_accel_receiver import build_receiver  # Else, use simulated data

accel_receiver = build_receiver()  # Starts the data receiver

app = create_smooth_stream_app(
    get_new_samples=accel_receiver.get_new_readings,  # Gets new accelerometer readings
    channels=("x", "y", "z"),  # Displays x, y and z values
    window_size=200,  # Keeps the latest 200 readings
    update_interval_ms=100,  # Updates the graph every 100 ms
    title="Live Phone Accelerometer",  
    y_label="Acceleration (g)",  
)

if __name__ == "__main__":
    app.run(debug=False)  # Starts the dashboard