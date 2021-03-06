# Licensed under a 3-clause BSD style license - see LICENSE.rst
from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np
from astropy import units as u

__all__ = ['Mask']


class Mask(object):
    """
    Class for a region mask.

    Parameters
    ----------
    data : array_like
        A 2D array of a region mask representing the fractional overlap
        of the region on the pixel grid.  This should be the full-sized
        (i.e. not truncated) array that is the direct output of one of
        the low-level "geometry" functions.

    bbox : `regions.BoundingBox`
        The bounding box for the region.

    Examples
    --------
    Usage examples are provided in the :ref:`gs-masks` section of the docs.
    """

    def __init__(self, data, bbox):
        self.data = np.asanyarray(data)
        if self.data.shape != bbox.shape:
            raise ValueError("Shape of data and bounding box should match")
        self.bbox = bbox

    @property
    def shape(self):
        """
        The shape of the mask data array.
        """
        return self.data.shape

    def __array__(self):
        """
        Array representation of the mask data array (e.g., for matplotlib).
        """
        return self.data

    def _overlap_slices(self, shape):
        """
        Calculate the slices for the overlapping part of the bounding box
        and an array of the given shape.

        Parameters
        ----------
        shape : tuple of int
            The ``(ny, nx)`` shape of array where the slices are to be
            applied.

        Returns
        -------
        slices_large : tuple of slices
            A tuple of slice objects for each axis of the large array,
            such that ``large_array[slices_large]`` extracts the region
            of the large array that overlaps with the small array.

        slices_small : slice
            A tuple of slice objects for each axis of the small array,
            such that ``small_array[slices_small]`` extracts the region
            of the small array that is inside the large array.
        """

        if len(shape) != 2:
            raise ValueError('input shape must have 2 elements.')

        xmin = self.bbox.ixmin
        xmax = self.bbox.ixmax
        ymin = self.bbox.iymin
        ymax = self.bbox.iymax

        if xmin >= shape[1] or ymin >= shape[0] or xmax <= 0 or ymax <= 0:
            # no overlap of the region with the data
            return None, None

        slices_large = (slice(max(ymin, 0), min(ymax, shape[0])),
                        slice(max(xmin, 0), min(xmax, shape[1])))

        slices_small = (slice(max(-ymin, 0),
                              min(ymax - ymin, shape[0] - ymin)),
                        slice(max(-xmin, 0),
                              min(xmax - xmin, shape[1] - xmin)))

        return slices_large, slices_small

    def to_image(self, shape):
        """
        Return an image of the mask in a 2D array of the given shape,
        taking any edge effects into account.

        Parameters
        ----------
        shape : tuple of int
            The ``(ny, nx)`` shape of the output array.

        Returns
        -------
        result : `~numpy.ndarray`
            A 2D array of the mask.
        """

        if len(shape) != 2:
            raise ValueError('input shape must have 2 elements.')

        mask = np.zeros(shape)

        try:
            mask[self.bbox.slices] = self.data
        except ValueError:    # partial or no overlap
            slices_large, slices_small = self._overlap_slices(shape)

            if slices_small is None:
                return None    # no overlap

            mask = np.zeros(shape)
            mask[slices_large] = self.data[slices_small]

        return mask

    def cutout(self, data, fill_value=0.):
        """
        Create a cutout from the input data over the mask bounding box,
        taking any edge effects into account.

        Parameters
        ----------
        data : array_like or `~astropy.units.Quantity`
            A 2D array on which to apply the region mask.

        fill_value : float, optional
            The value is used to fill pixels where the region mask
            does not overlap with the input ``data``.  The default is 0.

        Returns
        -------
        result : `~numpy.ndarray`
            A 2D array cut out from the input ``data`` representing the
            same cutout region as the region mask.  If there is a
            partial overlap of the region mask with the input data,
            pixels outside of the data will be assigned to
            ``fill_value``.  `None` is returned if there is no overlap
            of the region with the input ``data``.
        """

        data = np.asanyarray(data)
        cutout = data[self.bbox.slices]

        if cutout.shape != self.shape:
            slices_large, slices_small = self._overlap_slices(data.shape)

            if slices_small is None:
                return None    # no overlap

            cutout = np.zeros(self.shape, dtype=data.dtype)
            cutout[:] = fill_value
            cutout[slices_small] = data[slices_large]

            if isinstance(data, u.Quantity):
                cutout = u.Quantity(cutout, unit=data.unit)

        return cutout

    def multiply(self, data, fill_value=0.):
        """
        Multiply the region mask with the input data, taking any edge
        effects into account.

        The result is a mask-weighted cutout from the data.

        Parameters
        ----------
        data : array_like or `~astropy.units.Quantity`
            The 2D array to multiply with the region mask.

        fill_value : float, optional
            The value is used to fill pixels where the region mask does
            not overlap with the input ``data``.  The default is 0.

        Returns
        -------
        result : `~numpy.ndarray`
            A 2D mask-weighted cutout from the input ``data``.  If there
            is a partial overlap of the region mask with the input data,
            pixels outside of the data will be assigned to
            ``fill_value`` before being multipled with the mask.  `None`
            is returned if there is no overlap of the region with the
            input ``data``.
        """

        return self.cutout(data, fill_value=fill_value) * self.data
