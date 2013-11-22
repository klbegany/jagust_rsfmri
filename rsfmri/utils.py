import os, sys
import datetime
from glob import glob

import numpy as np

import nibabel
from nipype.interfaces.base import CommandLine
from nipype.utils import filemanip

## deal with relative import for now
cwd = os.getcwd()
sys.path.insert(0, cwd)
import nipype_ext

########################

def get_files(dir, globstr):
    """
    uses glob to find dir/globstr
    returns sorted list; number of files
    """
    searchstr = os.path.join(dir, globstr)
    files = glob(searchstr)
    files.sort()
    return files, len(files)


def make_datestr():
    now = datetime.datetime.now()
    return now.strftime('%Y_%m_%d_%H_%S')


def get_slicetime(nslices):
    """
    If TOTAL # SLICES = EVEN, then the excitation order when interleaved
    is EVENS first, ODDS second.
    If TOTAL # SLICES = ODD, then the excitation order when interleaved is
    ODDS first, EVENS second.

    Returns:
    sliceorder: list
        list containing the order of slice acquisition used for slicetime correction

    """
    if np.mod(nslices,2) == 0:
        sliceorder = np.concatenate((np.arange(2,nslices+1,2),
                                     np.arange(1,nslices+1,2)))
    else:
        sliceorder = np.concatenate((np.arange(1,nslices+1,2),
                                     np.arange(2,nslices+1,2)))
    # cast to a list for use with interface
    return list(sliceorder)
        

def get_slicetime_vars(infiles, TR=None):
    """
    uses nibabel to get slicetime variables
    Returns: 
    dict: dict
        nsclies : number of slices
        TA : acquisition Time
        TR: repetition Time
        sliceorder : array with slice order to run slicetime correction
    """
    if hasattr('__iter__', infiles):
        img = nibabel.load(infiles[0])
    else:
        img = nibabel.load(infiles)
    hdr = img.get_header()
    if TR is None:
        raise RuntimeError('TR is not defined ')
    shape = img.get_shape()
    nslices = shape[2]
    TA = TR - TR/nslices
    sliceorder = get_slicetime(nslices)
    return dict(nslices=nslices,
                TA = TA,
                TR = TR,
                sliceorder = sliceorder)


def zip_files(files):
    if not hasattr(files, '__iter__'):
        files = [files]
    for f in files:
        base, ext = os.path.splitext(f)
        if 'gz' in ext:
            # file already gzipped
            continue
        cmd = CommandLine('gzip %s' % f)
        cout = cmd.run()
        if not cout.runtime.returncode == 0:
            logging.error('Failed to zip %s'%(f))

def unzip_file(infile):
    """ looks for gz  at end of file,
    unzips and returns unzipped filename"""
    base, ext = os.path.splitext(infile)
    if not ext == '.gz':
        return infile
    else:
        if os.path.isfile(base):
            return base
        cmd = CommandLine('gunzip %s' % infile)
        cout = cmd.run()
        if not cout.runtime.returncode == 0:
            print 'Failed to unzip %s'%(infile)
            return None
        else:
            return base




def spm_realign_unwarp(infiles, matlab = 'matlab-spm8'):
    """ uses spm to run realign_unwarp
    Returns
    -------
    mean_img = File; mean generated by unwarp/realign

    realigned_files = Files; files unwarped and realigned

    parameters = File; file holding the trans rot params
    """
    
    startdir = os.getcwd()
    pth, _ = os.path.split(infiles[0])
    os.chdir(pth)    
    ru = nipype_ext.RealignUnwarp(matlab_cmd = matlab)
    ru.inputs.in_files = infiles
    ruout = ru.run()
    os.chdir(startdir)
    if not ruout.runtime.returncode == 0:
        print ruout.runtime.stderr
        return None, None, None
    return ruout.outputs.mean_image, ruout.outputs.realigned_files,\
           ruout.outputs.realignment_parameters

