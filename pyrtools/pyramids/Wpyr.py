import numpy as np
from .pyramid import Pyramid
from .pyr_utils import LB2idx, modulateFlip
from .filters import namedFilter
from .c.wrapper import corrDn, upConv
from ..tools.showIm import showIm
import matplotlib.pyplot as plt
from matplotlib import cm


class WaveletPyramid(Pyramid):

    #constructor
    def __init__(self, image, height='auto', filt='qmf9',
                 edgeType='reflect1'):

        super().__init__(image=image, edgeType=edgeType)

        self.initFilters(filter=filt)
        self.initHeight(height=height)
        self.buildPyr()
        self.pyrType = 'Wavelet'

    def initFilters(self, filter):
        self.lo_filter = self.parseFilter(filter)
        self.stag = (self.lo_filter.shape[0] + 1) % 2
        self.hi_filter = modulateFlip(self.lo_filter)
        # # if 1D filter, match to image dimensions
        # if self.lo_filter.ndim == 1 or self.lo_filter.shape[1] == 1:
        #     if self.image.shape[0] == 1:
        #         self.lo_filter = self.lo_filter.reshape(1, -1)
        #     elif self.image.shape[1] == 1:
        #         self.lo_filter = self.lo_filter.reshape(-1, 1)

    def initHeight(self, height):
        self.height = 1 + self.maxPyrHt(self.image.shape, self.lo_filter.shape)
        if isinstance(height, int):
            assert height <= self.height, "Error: cannot build pyramid higher than %d levels" % (self.height)
            self.height = height


    def buildNext(self, image):
        lfilt = self.lo_filter
        hfilt = self.hi_filter
        edgeType = self.edgeType
        stag = self.stag

        if len(image.shape) == 1 or image.shape[1] == 1:
            lolo = corrDn(image=image, filt=lfilt, edges=edgeType, step=(2,1), start=(stag,0))
            hihi = corrDn(image=image, filt=hfilt, edges=edgeType, step=(2,1), start=(1,0))
            return lolo, (hihi, )
        elif image.shape[0] == 1:
            lolo = corrDn(image=image, filt=lfilt, edges=edgeType, step=(1,2), start=(0,stag))
            hihi = corrDn(image=image, filt=hfilt, edges=edgeType, step=(1,2), start=(0,1))
            return lolo, (hihi, )
        else:
            lo = corrDn(image = image, filt = lfilt, edges = edgeType, step = (2,1), start = (stag,0))
            hi = corrDn(image = image, filt = hfilt, edges = edgeType, step = (2,1), start = (1,0))
            lolo = corrDn(image = lo, filt = lfilt.T, edges = edgeType, step = (1,2), start = (0,stag))
            lohi = corrDn(image = hi, filt = lfilt.T, edges = edgeType, step = (1,2), start = (0,stag))
            hilo = corrDn(image = lo, filt = hfilt.T, edges = edgeType, step = (1,2), start = (0,1))
            hihi = corrDn(image = hi, filt = hfilt.T, edges = edgeType, step = (1,2), start = (0,1))
            return lolo, (lohi, hilo, hihi)

    def buildPyr(self):
        im = self.image
        for lev in range(self.height - 1):
            im, higher_bands = self.buildNext(im)
            for band in higher_bands:
                self.pyr.append(band)
                self.pyrSize.append(band.shape)
        self.pyr.append(im)
        self.pyrSize.append(im.shape)

    # methods
    def numBands(self):
        if len(self.pyrSize[0]) == 1 or min(self.pyrSize[0]) == 1:
            return 1
        else:
            return 3

    def reconPyr(self, filt='qmf9', edges='reflect1', levs='all', bands='all'):
        # Optional args

        if isinstance(levs, str) and levs == 'all':
            levs = np.arange(self.height)
        else:
            levs = self.height - 1 - np.array(levs)
            assert (levs < self.height).any(), "Error: level numbers must be in the range [0, %d]" % self.height
        allLevs = np.arange(self.height)

        if isinstance(bands, str) and bands == "all":
            bands = np.arange(self.numBands())
        else:
            bands = np.array(bands)
            assert (bands >= 0).all(), "Error: band numbers must be larger than 0."
            assert (bands < self.numBands()).all(), "Error: band numbers must be smaller than %d." % self.bandNums()

        if isinstance(filt, str):
            filt = namedFilter(filt)
        hfilt = modulateFlip(filt).T

        # for odd-length filters, stagger the sampling lattices:
        if len(filt) % 2 == 0:
            stag = 2
        else:
            stag = 1

        idx = len(self.pyrSize)-1

        for lev in allLevs:

            if lev == 0:
                if 0 in levs:
                    res = self.pyr[len(self.pyr)-1]
                else:
                    res = np.zeros(self.pyr[len(self.pyr)-1].shape)
            elif lev > 0:
                # compute size of result image: assumes critical sampling
                if ( len(self.pyrSize[0]) == 1 or self.pyrSize[0][0] == 1 or
                     self.pyrSize[0][1] == 1 ):
                    resIdx = len(self.pyrSize)-lev-2
                    if self.pyrSize[0][0] == 1:
                        if lev == allLevs[-1]:
                            res_sz = (1, res_sz[1]*2)
                        else:
                            res_sz = self.pyrSize[resIdx]
                    elif self.pyrSize[0][1] == 1:
                        if lev == allLevs[-1]:
                            res_sz = (res_sz[0]*2, 1)
                        else:
                            res_sz = self.pyrSize[resIdx]
                else:
                    resIdx = len(self.pyrSize)-(3*(lev-1))-3
                    res_sz = (self.pyrSize[resIdx][0]+self.pyrSize[resIdx-1][0],
                              self.pyrSize[resIdx][1]+self.pyrSize[resIdx-1][1])
                    lres_sz = ([self.pyrSize[resIdx][0], res_sz[1]])
                    hres_sz = ([self.pyrSize[resIdx-1][0], res_sz[1]])
                imageIn = res.copy()
                if res_sz[0] == 1:
                    res = upConv(image = imageIn, filt = filt.T, edges = edges,
                                 step = (1,2), start = (0,stag-1),
                                 stop = res_sz).T
                elif res_sz[1] == 1:
                    res = upConv(image = imageIn, filt = filt, edges = edges,
                                 step = (2,1), start = (stag-1,0),
                                 stop = res_sz).T
                else:
                    ires = upConv(image = imageIn, filt = filt.T,
                                  edges = edges, step = (1,2),
                                  start = (0,stag-1), stop = lres_sz)
                    res = upConv(image = ires, filt = filt, edges = edges,
                                 step = (2,1), start = (stag-1,0),
                                 stop = res_sz)

                if ( len(self.pyrSize[0]) == 1 or self.pyrSize[0][0] == 1 or
                     self.pyrSize[0][1] == 1 ):
                    idx = resIdx + 1
                else:
                    idx = resIdx - 1

                if res_sz[0] ==1 and lev in levs:
                    res = upConv(image = self.band(idx), filt = hfilt,
                                 edges = edges, step = (1,2), start = (0,1),
                                 stop = res_sz, result = res)
                    idx -= 1
                elif res_sz[1] == 1 and lev in levs:
                    res = upConv(image = self.band(idx), filt = hfilt.T,
                                 edges = edges, step = (2,1), start = (1,0),
                                 stop = res_sz, result = res)
                    idx -= 1
                elif res_sz[0] != 1 and res_sz[1] != 1 and lev in levs:
                    res_test = res
                    if 0 in bands and lev in levs:
                        ires = upConv(image = self.band(idx), filt = filt.T,
                                      edges = edges, step = (1,2),
                                      start = (0, stag-1), stop = hres_sz)
                        res = upConv(image = ires, filt = hfilt.T,
                                     edges = edges, step = (2,1),
                                     start = (1,0), stop = res_sz,
                                     result = res)
                    idx += 1
                    if 1 in bands and lev in levs:
                        ires = upConv(image = self.band(idx), filt = hfilt,
                                      edges = edges, step = (1,2),
                                      start = (0,1), stop = lres_sz)
                        res = upConv(image = ires, filt = filt, edges = edges,
                                     step = (2,1), start = (stag-1,0),
                                     stop = res_sz, result = res)
                    idx += 1
                    if 2 in bands and lev in levs:
                        ires = upConv(image = self.band(idx), filt = hfilt,
                                      edges = edges, step = (1,2),
                                      start = (0,1), stop = hres_sz)
                        res = upConv(image = ires, filt = hfilt.T,
                                     edges = edges, step = (2,1),
                                     start = (1,0), stop = res_sz,
                                     result = res)
                    idx += 1
                # need to jump back n bands in the idx each loop
                if ( len(self.pyrSize[0]) == 1 or self.pyrSize[0][0] == 1 or
                     self.pyrSize[0][1] == 1 ):
                    idx = idx
                else:
                    idx -= 2*len(bands)
        return res

    def set1D(self, *args):
        if len(args) != 3:
            print('Error: three input parameters required:')
            print('  set(band, location, value)')
            print('  where band and value are integer and location is a tuple')
        print('%d %d %d' % (args[0], args[1], args[2]))
        print(self.pyr[args[0]][0][1])

    def pyrLow(self):
        return np.array(self.band(len(self.pyrSize)-1))

    def showPyr(self, prange = None, gap = 1, scale = None, disp = 'qt'):
        # determine 1D or 2D pyramid:
        if self.pyrSize[0][0] == 1 or self.pyrSize[0][1] == 1:
            nbands = 1
        else:
            nbands = 3

        if prange is None and nbands == 1:
            prange = 'auto1'
        elif prange is None and nbands == 3:
            prange = 'auto2'

        if scale is None and nbands == 1:
            scale = np.sqrt(2)
        elif scale is None and nbands == 3:
            scale = 2

        ht = self.height - 1
        nind = len(self.pyr)

        ## Auto range calculations:
        if prange == 'auto1':
            prange = np.ones((nind,1))
            mn = 0.0
            mx = 0.0
            for lnum in range(1,ht+1):
                for bnum in range(nbands):
                    idx = LB2idx(lnum, bnum, ht+2, nbands)
                    band = self.band(idx)/(np.power(scale,lnum))
                    prange[(lnum-1)*nbands+bnum+1] = np.power(scale,lnum-1)
                    bmn = np.amin(band)
                    bmx = np.amax(band)
                    mn = min([mn, bmn])
                    mx = max([mx, bmx])
            if nbands == 1:
                pad = (mx-mn)/12
                mn = mn-pad
                mx = mx+pad
            prange = np.outer(prange, np.array([mn, mx]))
            band = self.pyrLow()
            mn = np.amin(band)
            mx = np.amax(band)
            if nbands == 1:
                pad = (mx-mn)/12
                mn = mn-pad
                mx = mx+pad
            prange[nind-1,:] = np.array([mn, mx])
        elif prange == 'indep1':
            prange = np.zeros((nind,2))
            for bnum in range(nind):
                band = self.band(bnum)
                mn = band.min()
                mx = band.max()
                if nbands == 1:
                    pad = (mx-mn)/12
                    mn = mn-pad
                    mx = mx+pad
                prange[bnum,:] = np.array([mn, mx])
        elif prange == 'auto2':
            prange = np.ones(nind)
            sqsum = 0
            numpixels = 0
            for lnum in range(1,ht+1):
                for bnum in range(nbands):
                    band = self.band(LB2idx(lnum, bnum, ht, nbands))
                    band = band / np.power(scale,lnum-1)
                    sqsum += np.sum( np.power(band, 2) )
                    numpixels += band.shape[0] * band.shape[1]
                    prange[(lnum-1)*nbands+bnum+1] = np.power(scale, lnum-1)
            stdev = np.sqrt( sqsum / (numpixels-1) )
            prange = np.outer(prange, np.array([-3*stdev, 3*stdev]))
            band = self.pyrLow()
            av = np.mean(band)
            stdev = np.sqrt( np.var(band) )
            prange[nind-1,:] = np.array([av-2*stdev, av+2*stdev])
        elif prange == 'indep2':
            prange = np.zeros((nind,2))
            for bnum in range(nind-1):
                band = self.band(bnum)
                stdev = np.sqrt( np.var(band) )
                prange[bnum,:] = np.array([-3*stdev, 3*stdev])
            band = self.pyrLow()
            av = np.mean(band)
            stdev = np.sqrt( np.var(band) )
            prange[nind-1,:] = np.array([av-2*stdev, av+2*stdev])
        elif isinstance(prange, str):
            print("Error:Bad RANGE argument: %s'" % (prange))
        elif prange.shape[0] == 1 and prange.shape[1] == 2:
            scales = np.power(scale, list(range(ht)))
            scales = np.outer( np.ones((nbands,1)), scales )
            scales = np.array([1, scales, np.power(scale, ht)])
            prange = np.outer(scales, prange)
            band = self.pyrLow()
            prange[nind,:] += np.mean(band) - np.mean(prange[nind,:])


        if nbands == 1:   # 1D signal
            fig = plt.figure()
            #ax0 = fig.add_subplot(len(self.pyrSize), 1, 1)
            #ax0.set_frame_on(False)
            #ax0.get_xaxis().tick_bottom()
            #ax0.get_xaxis().tick_top()
            #ax0.get_yaxis().tick_right()
            #ax0.get_yaxis().tick_left()
            #ax0.get_yaxis().set_visible(False)
            for bnum in range(nind):
                band = self.band(bnum)
                plt.subplot(len(self.pyrSize), 1, bnum+1)
                plt.plot(band.T)
            plt.tight_layout()
            plt.show()
        else:
            colormap = cm.Greys_r
            bg = 255

            # compute positions of subbands
            llpos = np.ones((nind,2));

            for lnum in range(ht):
                ind1 = lnum*nbands
                xpos = self.pyrSize[ind1][1] + 1 + gap*(ht-lnum+1);
                ypos = self.pyrSize[ind1+1][0] + 1 + gap*(ht-lnum+1);
                llpos[ind1:ind1+3, :] = [[ypos, 1], [1, xpos], [ypos, xpos]]
            llpos[nind-1,:] = [1, 1]   # lowpass

            # make position list positive, and allocate appropriate image:
            llpos = llpos - ((np.ones((nind,1)) * np.amin(llpos, axis=0)) + 1) + 1
            llpos = llpos.astype(int)
            urpos = llpos + self.pyrSize
            d_im = np.ones((np.amax(urpos), np.amax(urpos))) * bg

            # paste bands into image, (im-r1)*(nshades-1)/(r2-r1) + 1.5
            nshades = 64;
            for bnum in range(nind):
                mult = (nshades-1) / (prange[bnum,1]-prange[bnum,0])
                d_im[llpos[bnum,0]:urpos[bnum,0],
                     llpos[bnum,1]:urpos[bnum,1]] = mult * self.band(bnum) + (1.5-mult*prange[bnum,0])

            if disp == 'qt':
                showIm(d_im, 'auto', 2)
            # elif disp == 'nb':
            #     JBhelpers.showIm(d_im, 'auto', 2)
