def center_x(bbox):
    return (bbox[0][0] + bbox[1][0]) / 2

def center_y(bbox):
    return (bbox[0][1] + bbox[2][1]) / 2

def y_close(y1, y2, tolerance=15):
    return abs(y1 - y2) <= tolerance
