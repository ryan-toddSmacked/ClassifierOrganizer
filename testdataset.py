"""
Download a subset of the MNIST digit dataset for testing the Chip Organizer.
"""

import os
import gzip
import urllib.request
from pathlib import Path
import numpy as np
from PIL import Image


def download_mnist_subset(output_dir='mnist_test_data', num_samples_per_digit=50):
    """
    Download and extract a subset of MNIST digits.
    
    Args:
        output_dir: Directory to save images
        num_samples_per_digit: Number of samples to save for each digit (0-9)
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    print("Downloading MNIST test dataset...")
    
    # MNIST URLs
    base_url = 'http://yann.lecun.com/exdb/mnist/'
    files = {
        'images': 't10k-images-idx3-ubyte.gz',
        'labels': 't10k-labels-idx1-ubyte.gz'
    }
    
    # Download files
    data = {}
    for key, filename in files.items():
        url = base_url + filename
        filepath = output_path / filename
        
        if not filepath.exists():
            print(f"Downloading {filename}...")
            try:
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:
                print(f"Error downloading from official source: {e}")
                print("Trying Google Cloud Storage mirror...")
                # Try alternative source
                url = f'https://storage.googleapis.com/cvdf-datasets/mnist/{filename}'
                urllib.request.urlretrieve(url, filepath)
        
        # Read the file
        with gzip.open(filepath, 'rb') as f:
            if key == 'images':
                # Skip header (16 bytes) and read images
                f.read(16)
                buf = f.read()
                data[key] = np.frombuffer(buf, dtype=np.uint8).reshape(-1, 28, 28)
            else:
                # Skip header (8 bytes) and read labels
                f.read(8)
                buf = f.read()
                data[key] = np.frombuffer(buf, dtype=np.uint8)
    
    images = data['images']
    labels = data['labels']
    
    print(f"\nExtracting {num_samples_per_digit} samples per digit...")
    
    # Count how many of each digit we've saved
    digit_counts = {i: 0 for i in range(10)}
    total_saved = 0
    
    # Iterate through the dataset and save samples
    for idx, (image, label) in enumerate(zip(images, labels)):
        label = int(label)
        
        # Check if we need more samples of this digit
        if digit_counts[label] < num_samples_per_digit:
            # Convert to PIL Image
            img = Image.fromarray(image, mode='L')
            
            # Save with digit in filename
            filename = f"digit_{label}_{digit_counts[label]:03d}.png"
            filepath = output_path / filename
            img.save(filepath)
            
            digit_counts[label] += 1
            total_saved += 1
            
            if total_saved % 50 == 0:
                print(f"Saved {total_saved} images...")
        
        # Stop when we have enough of all digits
        if all(count >= num_samples_per_digit for count in digit_counts.values()):
            break
    
    print(f"\n✓ Successfully saved {total_saved} images to {output_dir}/")
    print("\nDistribution:")
    for digit, count in sorted(digit_counts.items()):
        print(f"  Digit {digit}: {count} images")
    
    # Create a simple CSV ontology file (no header, just labels)
    csv_path = output_path / "mnist_labels.csv"
    with open(csv_path, 'w', encoding='utf-8') as f:
        for i in range(10):
            f.write(f"Digit-{i}\n")
    
    print(f"\n✓ Created ontology file: {csv_path}")
    print("\nYou can now:")
    print(f"  1. Load images from: {output_dir}/")
    print(f"  2. Load ontology from: {csv_path}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Download MNIST digit subset for testing')
    parser.add_argument('--output', '-o', default='mnist_test_data',
                        help='Output directory (default: mnist_test_data)')
    parser.add_argument('--samples', '-n', type=int, default=50,
                        help='Number of samples per digit (default: 50)')
    
    args = parser.parse_args()
    
    download_mnist_subset(args.output, args.samples)
