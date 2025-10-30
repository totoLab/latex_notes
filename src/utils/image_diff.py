"""
Image difference detection for comparing two images
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


class ImageDiff:
    """Class for comparing two images and detecting changes"""

    def __init__(self, image, new_image):
        self.image = image
        self.new_image = new_image

    @staticmethod
    def load_image(image_path):
        """Load an image from the specified path"""
        try:
            img = Image.open(image_path)
            return img
        except Exception as e:
            raise ValueError(f"Error loading image from {image_path}: {str(e)}")

    @staticmethod
    def get_pixels(image):
        """Extract pixels from an image and return as a numpy array matrix"""
        return np.array(image)

    @staticmethod
    def get_pixel_difference(pixels1, pixels2):
        """Calculate the absolute difference between two pixel matrices"""
        if pixels1.shape != pixels2.shape:
            raise ValueError(
                f"Pixel matrices must have the same shape. "
                f"Got {pixels1.shape} and {pixels2.shape}"
            )
        
        # Calculate absolute difference
        diff = np.abs(pixels1.astype(np.float32) - pixels2.astype(np.float32))
        
        return diff.astype(np.uint8)

    @staticmethod
    def matrix_to_image(pixel_matrix):
        """Create an image from a pixel matrix"""
        # Ensure the matrix is in the correct format (uint8)
        if pixel_matrix.dtype != np.uint8:
            pixel_matrix = pixel_matrix.astype(np.uint8)
        
        return Image.fromarray(pixel_matrix)

    @staticmethod
    def save_image(image, output_path):
        """Save an image to a file"""
        try:
            image.save(output_path)
        except Exception as e:
            raise ValueError(f"Error saving image to {output_path}: {str(e)}")

    @staticmethod
    def threshold_diff(diff_matrix, threshold=30):
        """Apply a threshold to the difference matrix to make small differences blacker"""
        # Create a copy to avoid modifying the original
        result = diff_matrix.copy().astype(np.float32)
        
        # Set values below threshold to 0 (black)
        result[result < threshold] = 0
        
        return result.astype(np.uint8)

    @staticmethod
    def _merge_overlapping_clusters(clusters):
        """Merge overlapping or nearby clusters"""
        if not clusters:
            return []
        
        merged = []
        used = set()
        
        for i, (x1, y1, r1) in enumerate(clusters):
            if i in used:
                continue
            
            # Start a new merged cluster
            group = [(x1, y1, r1)]
            used.add(i)
            
            # Find all clusters that overlap with this one or any in the group
            changed = True
            while changed:
                changed = False
                for j, (x2, y2, r2) in enumerate(clusters):
                    if j in used:
                        continue
                    
                    # Check if cluster j overlaps with any cluster in the group
                    for gx, gy, gr in group:
                        distance = np.sqrt((x2 - gx)**2 + (y2 - gy)**2)
                        if distance < (r2 + gr):  # Circles overlap
                            group.append((x2, y2, r2))
                            used.add(j)
                            changed = True
                            break
            
            # Merge the group into a single cluster
            if len(group) == 1:
                merged.append(group[0])
            else:
                # Calculate new center as weighted average
                total_area = sum(r**2 for _, _, r in group)
                new_x = sum(x * r**2 for x, y, r in group) / total_area
                new_y = sum(y * r**2 for x, y, r in group) / total_area
                
                # Calculate new radius to encompass all clusters
                new_radius = max(
                    np.sqrt((x - new_x)**2 + (y - new_y)**2) + r
                    for x, y, r in group
                )
                
                merged.append((new_x, new_y, new_radius))
        
        return merged

    @staticmethod
    def find_clusters(diff_matrix, min_cluster_size=10, merge_overlapping=True):
        """Find clusters of non-black pixels and return their centers and radii"""
        clusters = []
        
        # Convert diff_matrix to binary (non-black vs black)
        if len(diff_matrix.shape) == 3:
            # Multi-channel: check if any channel is non-zero
            binary = np.any(diff_matrix > 0, axis=2).astype(np.uint8)
        else:
            # Single channel
            binary = (diff_matrix > 0).astype(np.uint8)
        
        # Find connected components (clusters)
        labeled, num_features = ndimage.label(binary)
        
        # Process each cluster
        for cluster_id in range(1, num_features + 1):
            # Find pixels belonging to this cluster
            cluster_pixels = np.argwhere(labeled == cluster_id)
            
            # Skip small clusters
            if len(cluster_pixels) < min_cluster_size:
                continue
            
            # Get bounding box of the cluster
            min_row, min_col = cluster_pixels.min(axis=0)
            max_row, max_col = cluster_pixels.max(axis=0)
            
            # Calculate center and radius for the circle
            center_y = (min_row + max_row) / 2
            center_x = (min_col + max_col) / 2
            
            # Radius is the maximum distance from center to any corner, plus some padding
            radius = max(
                np.sqrt((max_row - center_y)**2 + (max_col - center_x)**2),
                np.sqrt((min_row - center_y)**2 + (min_col - center_x)**2)
            ) * 1.2  # Add 20% padding
            
            clusters.append((center_x, center_y, radius))
        
        # Merge overlapping clusters if requested
        if merge_overlapping:
            clusters = ImageDiff._merge_overlapping_clusters(clusters)
        
        return clusters

    @staticmethod
    def draw_circles(image, clusters, circle_color=(255, 0, 0), circle_width=2):
        """Draw circles on an image at specified locations"""
        # Create a copy of the image to draw on
        result_image = image.copy()
        draw = ImageDraw.Draw(result_image)
        
        # Draw each circle
        for center_x, center_y, radius in clusters:
            bbox = [
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius
            ]
            draw.ellipse(bbox, outline=circle_color, width=circle_width)
        
        return result_image

    def run(self):
        """Run the image difference detection pipeline"""
        matrix1, matrix2 = ImageDiff.get_pixels(self.image), ImageDiff.get_pixels(self.new_image)
        diff = ImageDiff.get_pixel_difference(matrix1, matrix2)
        diff_low_pass = ImageDiff.threshold_diff(diff)
        diff_image = ImageDiff.matrix_to_image(diff)
        clusters = ImageDiff.find_clusters(diff_low_pass)
        return clusters
