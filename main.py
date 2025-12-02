import sys
import io
import datetime
from printer import PrinterDriver
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import barcode
    from barcode.writer import ImageWriter
    HAS_BARCODE = True
except ImportError:
    HAS_BARCODE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None
DEFAULT_PRINTER_ADDRESS = "4679DDDC-9D5A-EFB0-E5C4-CDC425FCF876"

def text_to_pbm(text, width, font_size=24, padding=0, align='center', border=True, barcode_text=None, header_text=None):
    if not HAS_PILLOW:
        raise ImportError("Pillow is not installed. Cannot render text.")
    
    # Use default font or load one if available
    try:
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()

    # Calculate text size
    dummy_img = Image.new('1', (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate dimensions
    content_width = width
    # If border, add some margin inside
    margin = 10 if border else 0
    
    # Header logic
    header_img = None
    if header_text:
        try:
            header_font = ImageFont.load_default(size=55)
        except:
            header_font = ImageFont.load_default() # Fallback
            
        dummy_img = Image.new('1', (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), header_text, font=header_font)
        header_w = bbox[2] - bbox[0]
        header_h = bbox[3] - bbox[1]
        
        # Create header image
        header_img = Image.new('1', (width, header_h + 10), 1)
        h_draw = ImageDraw.Draw(header_img)
        h_x = (width - header_w) // 2
        h_draw.text((h_x, 0), header_text, font=header_font, fill=0)

    # Text wrapping logic
    lines = []
    words = text.split()
    current_line = []
    
    # Max width for text
    max_text_width = width - (margin * 2) - 10 # 5px padding on each side inside margin
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_text_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
                current_line = [word]
            else:
                # Word itself is too long, force split (basic char split)
                # For simplicity, just add it for now, or split chars
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(' '.join(current_line))
    
    if not lines:
        lines = [""]

    # Calculate total text height
    line_heights = []
    total_text_height = 0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        h = bbox[3] - bbox[1]
        # Add some line spacing
        h += 4 
        line_heights.append(h)
        total_text_height += h
    
    # Remove last line spacing
    if line_heights:
        total_text_height -= 4

    y = margin + 5 # top padding inside border
    
    # Barcode generation
    barcode_img = None
    if barcode_text and HAS_BARCODE:
        try:
            # Generate barcode (disable text)
            code128 = barcode.get('code128', barcode_text, writer=ImageWriter())
            # Render to BytesIO
            fp = io.BytesIO()
            code128.write(fp, options={'write_text': False, 'module_height': 5.0})
            fp.seek(0)
            barcode_img = Image.open(fp)
            
            # Resize barcode to fit within width (with some margin)
            max_bc_width = width - (margin * 2) - 10
            if barcode_img.width > max_bc_width:
                ratio = max_bc_width / barcode_img.width
                new_h = int(barcode_img.height * ratio)
                barcode_img = barcode_img.resize((max_bc_width, new_h), Image.LANCZOS)
            
        except Exception as e:
            print(f"Error generating barcode: {e}")

    # Calculate total height
    content_height = total_text_height + (margin * 2) + 10
    if header_img:
        content_height += header_img.height + 10 # space for header
        
    if barcode_img:
        content_height += barcode_img.height + 5 # space for barcode
        # Space for barcode text
        content_height += 15 
    
    img_height = content_height + padding
    
    # Create image (1-bit, white background)
    image = Image.new('1', (width, img_height), 1)
    draw = ImageDraw.Draw(image)
    
    current_y = margin + 5
    
    # Draw header
    if header_img:
        image.paste(header_img, (0, current_y))
        current_y += header_img.height + 10

    # Draw text lines
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        
        if align == 'center':
            x = (width - w) // 2
        elif align == 'right':
            x = width - w - margin
        else:
            x = margin
            
        draw.text((x, current_y), line, font=font, fill=0)
        current_y += line_heights[i]
    
    # Draw barcode
    if barcode_img:
        bc_x = (width - barcode_img.width) // 2
        bc_y = current_y + 10 # below text
        # Paste barcode (convert to 1-bit if needed, though paste handles it usually)
        # barcode_img is usually RGB or L from ImageWriter, need to threshold or dither?
        # Simple paste might work if we convert to 1-bit
        bc_1bit = barcode_img.convert('1')
        image.paste(bc_1bit, (bc_x, bc_y))
        
        # Draw barcode text manually
        try:
            bc_font = ImageFont.load_default()
            bbox = draw.textbbox((0, 0), barcode_text, font=bc_font)
            bc_text_w = bbox[2] - bbox[0]
            bc_text_x = (width - bc_text_w) // 2
            bc_text_y = bc_y + barcode_img.height + 2
            draw.text((bc_text_x, bc_text_y), barcode_text, font=bc_font, fill=0)
        except Exception as e:
            print(f"Error drawing barcode text: {e}")

    # Draw border if requested
    if border:
        # Draw a rectangle around the content area (excluding bottom padding)
        border_h = content_height
        draw.rectangle([2, 2, width-3, border_h-3], outline=0, width=3)

    # Convert to PBM bytes
    with io.BytesIO() as f:
        image.save(f, format='PPM')
        return io.BytesIO(f.getvalue())


def main():
    if HAS_RICH:
        console.print(Panel.fit("Initializing Printer Driver...", title="Cat Printer CLI", style="bold blue"))
    else:
        print("Initializing Printer Driver...")
        
    driver = PrinterDriver()
    
    try:
        # 1. Initial scan
        if HAS_RICH:
            with console.status("[bold green]Scanning for Bluetooth devices (4 seconds)..."):
                devices = driver.scan(everything=True)
        else:
            print("Scanning for Bluetooth devices (4 seconds)...")
            devices = driver.scan(everything=True)
        
        if not devices:
            if HAS_RICH: console.print("[bold red]No devices found.[/bold red]")
            else: print("No devices found.")
            return

        # Check for default printer
        default_device_index = None
        for i, device in enumerate(devices):
            if DEFAULT_PRINTER_ADDRESS and device.address == DEFAULT_PRINTER_ADDRESS:
                default_device_index = i
                break
        
        selected_index = -1
        
        if default_device_index is not None:
            if HAS_RICH: console.print(f"[bold green]Found default printer: {devices[default_device_index].name} ({devices[default_device_index].address})[/bold green]")
            else: print(f"Found default printer: {devices[default_device_index].name} ({devices[default_device_index].address})")
            selected_index = default_device_index
        else:
            if HAS_RICH:
                table = Table(title="Bluetooth Devices")
                table.add_column("Index", justify="right", style="cyan", no_wrap=True)
                table.add_column("Name", style="magenta")
                table.add_column("Address", style="green")
                
                for i, device in enumerate(devices):
                    table.add_row(str(i), device.name or "Unknown", device.address)
                
                console.print(table)
            else:
                print("\nFound {} devices:".format(len(devices)))
                for i, device in enumerate(devices):
                    print(f"{i}: {device.name or 'Unknown'} ({device.address})")

            while True:
                if HAS_RICH:
                    choice = Prompt.ask("Select device index to connect to (or 'q' to quit)")
                else:
                    choice = input("Select device index to connect to (or 'q' to quit): ")
                
                if choice.lower() in ('q', 'exit'):
                    if HAS_RICH: console.print("[yellow]Exiting.[/yellow]")
                    else: print("Exiting.")
                    return

                try:
                    selected_index = int(choice)
                    if 0 <= selected_index < len(devices):
                        break
                    else:
                        if HAS_RICH: console.print("[red]Invalid index.[/red]")
                        else: print("Invalid index.")
                except ValueError:
                    if HAS_RICH: console.print("[red]Invalid input.[/red]")
                    else: print("Invalid input.")

        device = devices[selected_index]
        if HAS_RICH: console.print(f"Connecting to [bold]{device.name or 'Unknown'}[/bold]...")
        else: print(f"Connecting to {device.name or 'Unknown'}...")
            
        driver.connect(device.name, device.address)
        if HAS_RICH:
            console.print("[bold green]Connected![/bold green]")
        else:
            print("Connected!")

        # 3. Input loop
        if HAS_RICH:
            console.print(Panel.fit(
                "Type text to print.\n"
                "Commands:\n"
                "  /size <n>  : Change font size\n"
                "  /pad <n>   : Change padding\n"
                "  /border    : Toggle border\n"
                "  q, exit    : Quit",
                title="Printer Ready",
                border_style="green"
            ))
        else:
            print("\n--- Printer Ready ---")
            print("Type text to print.")
            print("Commands:")
            print("  /size <n>  : Change font size (default: 24)")
            print("  /pad <n>   : Change bottom padding (default: 0)")
            print("  q, exit    : Quit")
        
        current_font_size = 24
        current_padding = 50
        current_border = True
        print_counter = 1

        while True:
            try:
                prompt_text = f"[{current_font_size}px]"
                if HAS_RICH:
                    text = Prompt.ask(f"[cyan]{prompt_text}[/cyan]")
                else:
                    text = input(f"{prompt_text}> ")
                    
                if text.lower() in ('q', 'exit', 'quit'):
                    break
                
                if not text:
                    continue
                
                if text.startswith('/size '):
                    try:
                        new_size = int(text.split(' ')[1])
                        if new_size > 0:
                            current_font_size = new_size
                            if HAS_RICH: console.print(f"[green]Font size set to {current_font_size}[/green]")
                            else: print(f"Font size set to {current_font_size}")
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
                            if HAS_RICH: console.print(f"[green]Padding set to {current_padding}[/green]")
                            else: print(f"Padding set to {current_padding}")
                        else:
                            print("Padding must be non-negative.")
                    except (IndexError, ValueError):
                        print("Usage: /pad <number>")
                    continue
                    
                if text.strip() == '/border':
                    current_border = not current_border
                    state = "ON" if current_border else "OFF"
                    if HAS_RICH: console.print(f"[green]Border set to {state}[/green]")
                    else: print(f"Border set to {state}")
                    continue

                # Convert string to bytes for the printer driver
                if HAS_RICH: console.print("[dim]Rendering text...[/dim]")
                else: print("Rendering text...")
                
                try:
                    width = driver.model.paper_width if driver.model else 384
                    
                    # Generate barcode text: DD-MM-YYYY-#N
                    date_str = datetime.datetime.now().strftime("%d-%m-%Y")
                    barcode_text = f"{date_str}-#{print_counter}"
                    header_text = f"#{print_counter}"
                    
                    data = text_to_pbm(text, width, font_size=current_font_size, padding=current_padding, border=current_border, barcode_text=barcode_text, header_text=header_text)
                    
                    if HAS_RICH: console.print("[bold blue]Printing...[/bold blue]")
                    else: print("Printing...")
                    
                    driver.print(data, mode='pbm')
                    
                    print_counter += 1
                    
                    if HAS_RICH: console.print("[bold green]Done.[/bold green]")
                    else: print("Done.")
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
