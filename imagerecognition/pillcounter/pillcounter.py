class PillCounter():
    def __init__(self, arg):
        self.arg = arg

    def count(self):
        import numpy as np
        import cv2
        import imutils

        kernel = np.ones((7, 7), np.uint8)
        kernel2 = np.ones((17, 17), np.uint8)
        # Imagen
        path = self.arg
        original1 = cv2.imread(path)
        original = imutils.resize(original1, width=800)

        # shifting
        shifted = cv2.pyrMeanShiftFiltering(original, 21, 81)

        # convert the mean shift image to grayscale, then apply Otsu's thresholding
        grises = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(grises, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # Eliminacion de ruido y llenar huecos negros
        height, width = thresh.shape
        if cv2.countNonZero(thresh) > height * width / 2:
            thresh = cv2.bitwise_not(thresh)

        erosion = cv2.erode(thresh, kernel, iterations=2)

        closing = cv2.morphologyEx(erosion, cv2.MORPH_CLOSE, kernel)

        opening = cv2.morphologyEx(closing, cv2.MORPH_OPEN, kernel2)

        # Deteccion de bordes
        canny = cv2.Canny(opening, 70, 190)

        # Buscamos contornos
        (contours, _) = cv2.findContours(canny.copy(),
                                         cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Output(contours)))
        return len(contours)
