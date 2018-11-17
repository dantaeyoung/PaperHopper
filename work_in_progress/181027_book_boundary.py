import numpy as np
import cv2
from matplotlib import pyplot as plt
import socket
import pickle


class Object_To_Find:
    def __init__(self, imgname, orb=None, flann=None):
        self.imgname = imgname
        self.img = cv2.imread(imgname, 0)
        self.orb = orb
        self.flann = flann
        self.kp, self.des = self.orb.detectAndCompute(self.img, None)

    def find_from_scene(self, scene_kp, scene_des):
        matches = flann.knnMatch(self.des, scene_des, k=2)
        polygon, center = self.find_match_polygon(matches, scene_kp)
        return polygon, center

    def find_match_polygon(self, matches, scene_kp):
        # store all the good matches as per Lowe's ratio test.

        good = []
        for match in matches:
            if(len(match) == 2):
                m,n = match
                if m.distance < 0.7*n.distance:
                    good.append(m)

        MIN_MATCH_COUNT = 20

        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([ self.kp[m.queryIdx].pt for m in good ]).reshape(-1,1,2)
            dst_pts = np.float32([ scene_kp[m.trainIdx].pt for m in good ]).reshape(-1,1,2)

            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC,5.0)

            if M is not None:

                matchesMask = mask.ravel().tolist()

                h,w = self.img.shape
                pts = np.float32([ [0,0],[0,h-1],[w-1,h-1],[w-1,0] ]).reshape(-1,1,2)

                dst = cv2.perspectiveTransform(pts,M)

                center = np.mean(dst, axis = 0)[0]
                return dst, center

        # NO MATCHES
        #print("Not enough matches are found - {}/{}".format(len(good),MIN_MATCH_COUNT))
        return None, None



###################


# start camera and create frame
cap = cv2.VideoCapture(0)
cv2.namedWindow("image")

#get frame dimensions
ret, frame = cap.read()
frame_height, frame_width = frame.shape[:2]

# feature stuff

FLANN_INDEX_KDTREE = 0
FLANN_INDEX_LSH = 6

index_params = dict(algorithm = FLANN_INDEX_LSH,
                   table_number = 6, # 12
                   key_size = 12,     # 20
                   multi_probe_level = 1) #2

search_params = dict(checks = 50)

flann = cv2.FlannBasedMatcher(index_params, search_params)
orb = cv2.ORB_create(nfeatures=2000)


# define books to look for
imglist = ["attentionbook.jpg", "ambientcommonsbook.jpg", "deschoolingsociety.jpg"]
objs_to_look_for = [Object_To_Find(img, orb=orb, flann=flann) for img in imglist]


# open UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
UDP_IP = "192.168.1.181"
UDP_PORT = 6666

# camera loop
while True:
    ret, frame = cap.read()

    scene_kp, scene_des = orb.detectAndCompute(frame, None)

    results = [obj.find_from_scene(scene_kp, scene_des) for obj in objs_to_look_for ]

    for coords, center in results:
        if(coords is not None):
            frame = cv2.polylines(frame,[np.int32(coords)],True,255,3, cv2.LINE_AA)
            cv2.circle(frame, tuple(center), 5, (0,255,0), -1)

    centers_with_names = zip([obj.imgname for obj in objs_to_look_for ], [center.tolist() if (center is not None) else [None, None] for coords,center in results])

    goodcoords = [center.tolist() for coords,center in results if coords is not None]
    goodnames = [name for name, center in centers_with_names if center[0] is not None ]
#    print(list(zip(goodcoords, goodnames)))

    sock.sendto(bytes(str(list(zip(goodcoords, goodnames))), "utf-8"), (UDP_IP, UDP_PORT))


    cv2.imshow("image", frame)


    key = cv2.waitKey(1) & 0xFF
    # if the 'c' key is pressed, break from the loop
    if key == ord("q"):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
