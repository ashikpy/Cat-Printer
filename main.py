import sys
import io
from printer import PrinterDriver
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

def text_to_pbm(text, width, font_size=24, padding=0):
    if not HAS_PILLOW:
        raise ImportError("Pillow is not installed. Cannot render text.")
    
    # Use default font or load one if available
    try:
        # Try to load a default font with specified size
        font = ImageFont.load_default(size=font_size)
    except Exception:
        # Fallback for older Pillow versions or if size param fails
        font = ImageFont.load_default()

    # Calculate text size
    # ImageFont.getbbox or getsize (deprecated)
    dummy_img = Image.new('1', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Add some padding
    img_width = width
    img_height = text_height + 10 + padding # default 10 + extra padding
    
    # Create image (1-bit, white background)
    image = Image.new('1', (img_width, img_height), 1)
    draw = ImageDraw.Draw(image)
    
    # Draw text (black)
    draw.text((0, 5), text, font=font, fill=0)
    
    # Convert to PBM bytes
    with io.BytesIO() as f:
        image.save(f, format='PPM') # Pillow saves 1-bit images as P4 PBM when format is PPM/PBM
        return io.BytesIO(f.getvalue())


def main():
    print("Initializing Printer Driver...")
    driver = PrinterDriver()
    
    try:
        # 1. Initial scan of bluetooth devices
        print("Scanning for Bluetooth devices (4 seconds)...")
        # scan(everything=True) returns a list of BLEDevice objects
        devices = driver.scan(everything=True)
        
        if not devices:
            print("No Bluetooth devices found.")
            return

        print(f"\nFound {len(devices)} devices:")
        valid_devices = []
        for i, device in enumerate(devices):
            name = device.name or "Unknown"
            print(f"{i}: {name} ({device.address})")
            valid_devices.append(device)

        # 2. Prompt for device selection
        selected_device = None
        while selected_device is None:
            try:
                selection = input("\nSelect device index to connect to (or 'q' to quit): ")
                if selection.lower() == 'q':
                    print("Exiting.")
                    return
                
                index = int(selection)
                if 0 <= index < len(valid_devices):
                    selected_device = valid_devices[index]
                else:
                    print("Invalid index. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

        print(f"Connecting to {selected_device.name or selected_device.address}...")
        driver.connect(selected_device.name, selected_device.address)
        print("Connected!")

        # 3. Input loop for printing
        print("\n--- Printer Ready ---")
        print("Type text to print.")
        print("Commands:")
        print("  /size <n>  : Change font size (default: 24)")
        print("  /pad <n>   : Change bottom padding (default: 0)")
        print("  q, exit    : Quit")
        
        current_font_size = 24
        current_padding = 50 # Default padding as requested "need some padding"

        while True:
            try:
                text = input(f"[{current_font_size}px]> ")
                if text.lower() in ('q', 'exit'):
                    break
                
                if not text:
                    continue
                
                if text.startswith('/size '):
                    try:
                        new_size = int(text.split(' ')[1])
                        if new_size > 0:
                            current_font_size = new_size
                            print(f"Font size set to {current_font_size}")
                        else:
                            print("Size must be positive.")
                    except (IndexError, ValueError):
                        print("Usage: /size <number>")
                    continue
                
                if text.startswith('/pad '):
                    try:
                        new_pad = int(text.split(' ')[1])
                        if new_pad >= 0:
                            current_padding = new_pad
                            print(f"Padding set to {current_padding}")
                        else:
                            print("Padding must be non-negative.")
                    except (IndexError, ValueError):
                        print("Usage: /pad <number>")
                    continue

                # Convert string to bytes for the printer driver
                # The driver expects a file-like object (BufferedIOBase)
                # We use Pillow to render text to PBM image
                print("Rendering text...")
                try:
                    # Width is usually 384 for these printers (Cat printer)
                    # We can get it from driver.model.paper_width if connected
                    width = driver.model.paper_width if driver.model else 384
                    data = text_to_pbm(text, width, font_size=current_font_size, padding=current_padding)
                    
                    print("Printing...")
                    driver.print(data, mode='pbm') # Use PBM mode
                    print("Done.")
                except ImportError:
                    print("Error: Pillow not installed. Please install it to print text.")
                except Exception as e:
                    print(f"Error rendering/printing: {e}")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error during printing: {e}")

    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("Cleaning up...")
        driver.unload()
        print("Goodbye.")

if __name__ == "__main__":
    main()
