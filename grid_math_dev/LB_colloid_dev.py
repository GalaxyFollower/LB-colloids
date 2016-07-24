import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy import interpolate
import colloid_math as cm
import h5py as H
import optparse
import sys


class HDF5_reader:
    def __init__(self, HDF_name):
        hdf = H.File(HDF_name, 'r+')
        self.imarray = hdf['Binary_image'][()]
        self.uarray = hdf['results/uarray'][()]
        self.yu = hdf['results/uarray'][()][0]
        self.xu = hdf['results/uarray'][()][1]

class Gridarray:
    def __init__(self, arr, gridres, gridsplit, solid=True):
        '''
        Gridarray class creates arrays of distances from pore spaces, corrects for
        interpolation effects at pore boundaries, and creates vector arrays that are
        later used to give direction to forces.
        
        Inputs:
        -------
        arr: (np.array, np.bool) Array of boolean porous media (segmented image array)
        gridres: (float) model resolution in meters
        gridsplit: (int) interpolation factor for refining grid mesh
        solid: (bool) solid phase boolean identifier

        Defaults:
        ---------
        solid: True

        Returns:
        --------
        gridx: (np.array, np.float) Array of distances from nearest solid phase in the x-direction
        gridy: (np.array, np.float) Array of distances from nearest solid phase in the y-direction
        vector_x: (np.array, np.float) Array of specific vector directions in the x-direction (-1 == left, 1 == right)
        vector_y: (np.array, np.float) Array of specific vector directions in the y-direction (-1 == down, 1 == up)
        
        '''
        self.yarr = np.copy(arr.T)
        self._vimgx, self._vimgy = self._create_vector_array(arr, solid)
        self.gridx, self.vector_x = self._arrx(arr, self._vimgx, gridres, gridsplit)
        self.gridy, self.vector_y = self._arry(self.yarr, self._vimgy, gridres, gridsplit)

    def _create_vector_array(self, img, solid):
        '''
        creates an x-dir copy and y-dir copy of the image domain for vector
        directions to populate.
        '''
        vimgx = np.copy(img)
        vimgy = np.copy(img.T)
        vimgx[vimgx == solid] = np.nan
        vimgy[vimgy == solid] = np.nan
        return vimgx, vimgy

    def _arrx(self, arr, vector_x, gridres, gridsplit):
        '''
        Method that handles looping through array and sends it to distance_gridx
        '''
        for line in range(len(arr)):
            arr[line], vector_x[line] = self._distance_gridx(arr[line], vector_x[line], gridres, gridsplit)
        return arr, vector_x

    def _arry(self, yarr, vector_y, gridres, gridsplit):
        '''
        Method that handles looping through array and sends it to distance_gridy
        '''
        for line in range(len(yarr)):
            ylen = len(yarr[0])
            yarr[line], vector_y[line] = self._distance_gridy(yarr[line], vector_y[line], gridres, ylen, gridsplit)
        return yarr.T, vector_y.T
    
    def _distance_gridx(self, line, vline, gridres, gridsplit):
        '''
        Method uses linear interpolation to correct pore boundary space

        Follows by creating an array of pore boundaries and then counts the distance
        from the nearest solid. It also creates a a vector direction array that corresponds.
        '''
        rplc = np.linspace(0, 1, gridsplit)
        rplc = rplc[gridsplit/2:]
        for i in rplc:
            line[i] = 1.    # pore space == 0, solid is still 1.
        line[line < 1] = 0. # linear interpolation also interpolates pore
        line[line > 1] = 0. # boundaries, this block corrects that error

        # create an array of pore boundaries from binary system
        boundary= np.where(np.abs(np.diff(line)) >= 1)[0]
        try:
            for i in range(1, len(boundary), 2):
                rbound = boundary[i] + 1
                lbound = boundary[i-1]
                gap = rbound - lbound

                if gap % 2 == 0:
                    gap = gap//2
                    left = np.arange(1, gap + 1)*gridres
                    right = left[::-1]
                    line[lbound:rbound] = np.append(left, right)

                    left = np.ones(gap)*-1
                    right = np.ones(gap)
                    vline[lbound:rbound] = np.append(left, right)

                else:
                    gap = gap//2
                    left = np.arange(1, gap + 1)*gridres
                    right = left[::-1]
                    adjust = (len(left) + 1)*gridres
                    left = np.append(left, adjust)
                    line[lbound:rbound] = np.append(left, right)

                    left = np.ones(gap + 1)*-1
                    right = np.ones(gap)
                    vline[lbound:rbound] = np.append(left, right)
                    
        except IndexError:
            print 'volume does not percolate'
            sys.exit()
        return line, vline

    def _distance_gridy(self, line, vline, gridres, ylen, gridsplit):
        '''
        Method uses linear interpolation to correct pore boundary space

        Follows by creating an array of pore boundaries and then counts the distance
        from the nearest solid. It also creates a a vector direction array that corresponds.
        '''
        rplc = np.linspace(0, 1, gridsplit)
        rplc = rplc[gridsplit/2:]
        for i in rplc:
            line[i] = 1.    # pore space == 0, solid is still 1.
        line[line > 1.] = 0. # linear interpolation also interpolates pore
        line[line < 1.] = 0. # boundaries, this block corrects that error

        # create an array of pore boundaries from binary system
        boundary= np.where(np.abs(np.diff(line)) >= 1)[0]
        
        if len(boundary) > 0:
            rbound = boundary[1] + 1 
            lbound = 0
            top = np.arange(rbound, lbound, -1)*gridres
            line[lbound:rbound] = top
            vtop = np.ones(len(top))*-1
            vline[lbound:rbound] = vtop
            
               
            for i in range(3, len(boundary), 2):
                rbound = boundary[i] + 1
                lbound = boundary[i-1] + 1
                gap = rbound - lbound
                if gap % 2 == 0:
                    gap = gap//2
                    left = np.arange(1, gap + 1)*gridres
                    right = left[::-1]
                    line[lbound:rbound] = np.append(left, right)

                    left = np.ones(gap)
                    right = np.ones(gap)*-1
                    vline[lbound:rbound] = np.append(left, right)
                    
                else:
                    gap = gap//2
                    left = np.arange(1, gap + 1)*gridres
                    right = left[::-1]
                    adjust = (len(left) + 1)*gridres
                    left = np.append(left, adjust)
                    line[lbound:rbound] = np.append(left, right)

                    left = np.ones(gap + 1)
                    right = np.ones(gap)*-1
                    vline[lbound:rbound] = np.append(left, right)
                    
            rbound = ylen
            lbound = boundary[-1] + 1
            gap = rbound - lbound
            bottom =np.arange(1, gap + 1)*gridres
            line[lbound:rbound] = bottom

            bottom = np.ones(gap)
            vline[lbound:rbound] = bottom
        else:
            pass
        return line, vline

def LB_varray(LBv, img):
    vel = np.zeros((len(LB.yu),len(LB.yu[0])))
    invert = np.invert(img)
    vel = np.array([LBv[i]*invert[i] for i in range(len(LBv))])
    print vel.shape
    return vel

def interp_v(LBv, gridsplit):
    ylen = len(LBv)
    xlen = len(LBv[0])
    xindex = np.arange(0,xlen)
    yindex = np.arange(0,ylen)
    xnew = np.arange(0, xlen-1+(1./gridsplit), 1./gridsplit)
    ynew = np.arange(0, ylen-1+(1./gridsplit), 1./gridsplit)
    f = interpolate.interp2d(xindex, yindex, LBv, kind='linear')
    znew = f(xnew, ynew)
    return znew

LB = HDF5_reader('Synthetic255.hdf5')
gridsplit = 10
gridres = 1e-6/gridsplit

LBy = LB_varray(LB.yu, LB.imarray)
LBx = LB_varray(LB.xu, LB.imarray)
#LBv = np.sqrt(LB.yu*LB.yu+LB.xu*LB.xu)
#LBvp = LB_varray(LBv, LB.imarray)
#print LBx, LBy

#plt.imshow(LBvp, interpolation='nearest')
#plt.colorbar()
#plt.show()

#### interpolate over grid array and interpolate veloctity profiles ####
#Col_vp = interp_v(LBvp, gridsplit)
LBy = interp_v(LBy, gridsplit)
LBx = interp_v(LBx, gridsplit)
Col_img = interp_v(LB.imarray, gridsplit)

### Use grids function to measure distance from pore space and correct
### boundaries for interpolation effects. 
Grids = Gridarray(Col_img, gridres, gridsplit)
xArr = Grids.gridx
yArr = Grids.gridy


vxArr = Grids.vector_x
vyArr = Grids.vector_y

xArr[LBx == 0.] = np.nan
yArr[LBy == 0.] = np.nan
vxArr[LBx == 0.] = np.nan
vyArr[LBy == 0.] = np.nan

#cfactor and drag forces pass testing, note that if res/grid_res > colloid_r
#warnings are thrown by numpy

cfactor = cm.Gap(xArr, yArr)

drag_forces = cm.Drag(LBx, LBy, LBx, LBy, cfactor.f1, cfactor.f2,
                      cfactor.f3, cfactor.f4)

drag_forces.drag_x
drag_forces.drag_y


plt.imshow(vxArr, interpolation='nearest')
plt.colorbar()
plt.show()

plt.imshow(vyArr, interpolation='nearest')
plt.colorbar()
plt.show()
print xArr, yArr
xArr = np.ma.masked_where(yArr == 1., xArr)
plt.imshow(xArr, interpolation = 'nearest')
plt.colorbar()
plt.show()

yArr = np.ma.masked_where(yArr == 1., yArr)
plt.imshow(yArr, interpolation = 'nearest')
plt.colorbar()
plt.show()

'''
plt.imshow(Col_img, cmap=mpl.cm.Accent, interpolation='nearest')
Col_vp = np.ma.masked_where(Col_vp == 0, Col_vp)
plt.imshow(Col_vp, interpolation = 'nearest')
plt.colorbar()
plt.show()
'''
