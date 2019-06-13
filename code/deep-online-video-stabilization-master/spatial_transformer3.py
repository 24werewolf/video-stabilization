# Copyright 2016 The TensorFlow Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import tensorflow as tf
from config import *
import math

def transformer(U, theta, name='SpatialTransformer', **kwargs):
    """Spatial Transformer Layer

    Implements a spatial transformer layer as described in [1]_.
    Based on [2]_ and edited by David Dao for Tensorflow.

    Parameters
    ----------
    U : float
        The output of a convolutional net should have the
        shape [num_batch, height, width, num_channels].
    theta: float
        The output of the
        localisation network should be [num_batch, 6].
    out_size: tuple of two ints
        The size of the output of the network (height, width)

    References
    ----------
    .. [1]  Spatial Transformer Networks
            Max Jaderberg, Karen Simonyan, Andrew Zisserman, Koray Kavukcuoglu
            Submitted on 5 Jun 2015
    .. [2]  https://github.com/skaae/transformer_network/blob/master/transformerlayer.py

    Notes
    -----
    To initialize the network to the identity transform init
    ``theta`` to :
        identity = np.array([[1., 0., 0.],
                             [0., 1., 0.]])
        identity = identity.flatten()
        theta = tf.Variable(initial_value=identity)

    """

    def _repeat(x, n_repeats):
        with tf.variable_scope('_repeat'):
            rep = tf.transpose(
                tf.expand_dims(tf.ones(shape=tf.stack([n_repeats, ])), 1), [1, 0])
            rep = tf.cast(rep, 'int32')
            x = tf.matmul(tf.reshape(x, (-1, 1)), rep)
            return tf.reshape(x, [-1])

    def _interpolate(im, x, y, out_size):  
        with tf.variable_scope('_interpolate'):
            # constants
            num_batch = tf.shape(im)[0]
            height = tf.shape(im)[1]
            width = tf.shape(im)[2]
            channels = tf.shape(im)[3]

            x = tf.cast(x, 'float32')
            y = tf.cast(y, 'float32')
            height_f = tf.cast(height, 'float32')
            width_f = tf.cast(width, 'float32')
            out_height = out_size[0]
            out_width = out_size[1]
            zero = tf.zeros([], dtype='int32')
            max_y = tf.cast(tf.shape(im)[1] - 1, 'int32')
            max_x = tf.cast(tf.shape(im)[2] - 1, 'int32')

            # scale indices from [-1, 1] to [0, width/height]
            x = (x + 1.0)*(width_f) / 2.0
            y = (y + 1.0)*(height_f) / 2.0

            # do sampling
            x0 = tf.cast(tf.floor(x), 'int32')
            x1 = x0 + 1
            y0 = tf.cast(tf.floor(y), 'int32')
            y1 = y0 + 1

            x0 = tf.clip_by_value(x0, zero, max_x)
            x1 = tf.clip_by_value(x1, zero, max_x)
            y0 = tf.clip_by_value(y0, zero, max_y)
            y1 = tf.clip_by_value(y1, zero, max_y)
            dim2 = width
            dim1 = width*height
            base = _repeat(tf.range(num_batch)*dim1, out_height*out_width)
            base_y0 = base + y0*dim2
            base_y1 = base + y1*dim2
            idx_a = base_y0 + x0
            idx_b = base_y1 + x0
            idx_c = base_y0 + x1
            idx_d = base_y1 + x1

            # use indices to lookup pixels in the flat image and restore
            # channels dim
            im_flat = tf.reshape(im, tf.stack([-1, channels]))
            im_flat = tf.cast(im_flat, 'float32')
            Ia = tf.gather(im_flat, idx_a)
            Ib = tf.gather(im_flat, idx_b)
            Ic = tf.gather(im_flat, idx_c)
            Id = tf.gather(im_flat, idx_d)

            # and finally calculate interpolated values
            x0_f = tf.cast(x0, 'float32')
            x1_f = tf.cast(x1, 'float32')
            y0_f = tf.cast(y0, 'float32')
            y1_f = tf.cast(y1, 'float32')
            wa = tf.expand_dims(((x1_f-x) * (y1_f-y)), 1)
            wb = tf.expand_dims(((x1_f-x) * (y-y0_f)), 1)
            wc = tf.expand_dims(((x-x0_f) * (y1_f-y)), 1)
            wd = tf.expand_dims(((x-x0_f) * (y-y0_f)), 1)
            output = tf.add_n([wa*Ia, wb*Ib, wc*Ic, wd*Id])
            return output

    def _meshgrid(height, width):
        with tf.variable_scope('_meshgrid'):
            # This should be equivalent to:
            #  x_t, y_t = np.meshgrid(np.linspace(-1, 1, width),
            #                         np.linspace(-1, 1, height))
            #  ones = np.ones(np.prod(x_t.shape))
            #  grid = np.vstack([x_t.flatten(), y_t.flatten(), ones])
            x_t = tf.matmul(tf.ones(shape=tf.stack([height, 1])),
                            tf.transpose(tf.expand_dims(tf.linspace(-1.0, 1.0, width), 1), [1, 0]))
            y_t = tf.matmul(tf.expand_dims(tf.linspace(-1.0, 1.0, height), 1),
                            tf.ones(shape=tf.stack([1, width])))

            x_t_flat = tf.reshape(x_t, (1, -1))
            y_t_flat = tf.reshape(y_t, (1, -1))

            ones = tf.ones_like(x_t_flat)
            grid = tf.concat([x_t_flat, y_t_flat, ones], 0)
            return grid

    def pinv(A):
        return tf.matrix_inverse(A + tf.eye(8) * 1e-4) 

    # batch_size*8
    #output: batch_size*9
    def get_H(ori, tar): 
        num_batch = tf.shape(ori)[0]
        with tf.variable_scope('get_H'):
            one = tf.ones([num_batch, 1])
            zero = tf.zeros([num_batch, 1])
            x = [tf.slice(ori, [0, 0], [-1, 1]), tf.slice(ori, [0, 2], [-1, 1]), tf.slice(ori, [0, 4], [-1, 1]), tf.slice(ori, [0, 6], [-1, 1])]
            y = [tf.slice(ori, [0, 1], [-1, 1]), tf.slice(ori, [0, 3], [-1, 1]), tf.slice(ori, [0, 5], [-1, 1]), tf.slice(ori, [0, 7], [-1, 1])]
            u = [tf.slice(tar, [0, 0], [-1, 1]), tf.slice(tar, [0, 2], [-1, 1]), tf.slice(tar, [0, 4], [-1, 1]), tf.slice(tar, [0, 6], [-1, 1])]
            v = [tf.slice(tar, [0, 1], [-1, 1]), tf.slice(tar, [0, 3], [-1, 1]), tf.slice(tar, [0, 5], [-1, 1]), tf.slice(tar, [0, 7], [-1, 1])]

            A_ = []
            A_.extend([x[0], y[0], one, zero, zero, zero, -x[0] * u[0], -y[0] * u[0]])
            A_.extend([x[1], y[1], one, zero, zero, zero, -x[1] * u[1], -y[1] * u[1]])
            A_.extend([x[2], y[2], one, zero, zero, zero, -x[2] * u[2], -y[2] * u[2]])
            A_.extend([x[3], y[3], one, zero, zero, zero, -x[3] * u[3], -y[3] * u[3]])
            A_.extend([zero, zero, zero, x[0], y[0], one, -x[0] * v[0], -y[0] * v[0]])
            A_.extend([zero, zero, zero, x[1], y[1], one, -x[1] * v[1], -y[1] * v[1]])
            A_.extend([zero, zero, zero, x[2], y[2], one, -x[2] * v[2], -y[2] * v[2]])
            A_.extend([zero, zero, zero, x[3], y[3], one, -x[3] * v[3], -y[3] * v[3]])
            A = tf.reshape(tf.concat(A_, axis=1), [num_batch, 8, 8])
            b_ = [u[0], u[1], u[2], u[3], v[0],v[1], v[2], v[3]]
            b  = tf.reshape(tf.concat(b_, axis=1), [num_batch, 8, 1])
            
            #ans = tf.concat([tf.reshape(tf.matmul(tf.matrix_inverse(A), b), [num_batch, 8]), tf.ones([num_batch, 1])], axis=1)
            ans = tf.concat([tf.reshape(tf.matmul(pinv(A), b), [num_batch, 8]), tf.ones([num_batch, 1])], axis=1)

        return ans

    #input:  batch_size*(grid_h+1)*(grid_w+1)*2
    #output: batch_size*grid_h*grid_w*9
    def get_Hs(theta): 
        with tf.variable_scope('get_Hs'):
            num_batch = tf.shape(theta)[0]
            h = 2.0 / grid_h
            w = 2.0 / grid_w
            Hs = []
            for i in range(grid_h):
                for j in range(grid_w):
                    hh = i * h - 1
                    ww = j * w - 1
                    ori = tf.tile(tf.constant([ww, hh, ww + w, hh, ww, hh + h, ww + w, hh + h], shape=[1, 8], dtype=tf.float32), multiples=[num_batch, 1])
                    id = i * (grid_w + 1) + grid_w
                    tar = tf.concat([tf.slice(theta, [0, i, j, 0], [-1, 1, 1, -1]), tf.slice(theta, [0, i, j + 1, 0], [-1, 1, 1, -1]), 
                    tf.slice(theta, [0, i + 1, j, 0], [-1, 1, 1, -1]), tf.slice(theta, [0, i + 1, j + 1, 0], [-1, 1, 1, -1])], axis=1)
                    tar = tf.reshape(tar, [num_batch, 8])
                    #tar = tf.Print(tar, [tf.slice(ori, [0, 0], [1, -1])],message="[ori--i:"+str(i)+",j:"+str(j)+"]:", summarize=100,first_n=5)
                    #tar = tf.Print(tar, [tf.slice(tar, [0, 0], [1, -1])],message="[tar--i:"+str(i)+",j:"+str(j)+"]:", summarize=100,first_n=5)
                    Hs.append(tf.reshape(get_H(ori, tar), [num_batch, 1, 9]))   
            Hs = tf.reshape(tf.concat(Hs, axis=1), [num_batch, grid_h, grid_w, 9], name='Hs')
        return Hs 

    def _meshgrid2(height, width, sh, eh, sw, ew):
        hn = eh - sh + 1
        wn = ew - sw + 1

        x_t = tf.matmul(tf.ones(shape=tf.stack([hn, 1])),
                        tf.transpose(tf.expand_dims(tf.slice(tf.linspace(-1.0, 1.0, width), [sw], [wn]), 1), [1, 0]))
        y_t = tf.matmul(tf.expand_dims(tf.slice(tf.linspace(-1.0, 1.0, height), [sh], [hn]), 1),
                        tf.ones(shape=tf.stack([1, wn])))

        x_t_flat = tf.reshape(x_t, (1, -1))
        y_t_flat = tf.reshape(y_t, (1, -1))

        ones = tf.ones_like(x_t_flat)
        grid = tf.concat([x_t_flat, y_t_flat, ones], 0)
        return grid



    def _transform3(theta, input_dim):
        with tf.variable_scope('_transform'):
            num_batch = tf.shape(input_dim)[0]
            num_channels = tf.shape(input_dim)[3]
            theta = tf.cast(theta, 'float32')
            Hs = get_Hs(theta)
            print("!@#$%^==========================")
            print(Hs)
            print("!@#$%^==========================")
            gh = int(math.floor(height / grid_h))
            gw = int(math.floor(width / grid_w))
            x_ = []
            y_ = []
            for i in range(grid_h):
                row_x_ = []
                row_y_ = []
                for j in range(grid_w):
                    H = tf.reshape(tf.slice(Hs, [0, i, j, 0], [-1, 1, 1, -1]), [num_batch, 3, 3])
                    sh = i * gh
                    eh = (i + 1) * gh - 1
                    sw = j * gw
                    ew = (j + 1) * gw - 1
                    if (i == grid_h - 1):
                        eh = height - 1
                    if (j == grid_w - 1):
                        ew = width - 1
                    grid = _meshgrid2(height, width, sh, eh, sw, ew)
                    grid = tf.expand_dims(grid, 0)
                    grid = tf.tile(grid, [num_batch, 1, 1])

                    T_g = tf.matmul(H, grid)
                    x_s = tf.slice(T_g, [0, 0, 0], [-1, 1, -1])
                    y_s = tf.slice(T_g, [0, 1, 0], [-1, 1, -1])
                    z_s = tf.slice(T_g, [0, 2, 0], [-1, 1, -1])
         
                    z_s_flat = tf.reshape(z_s, [-1])
                    t_1 = tf.ones(shape = tf.shape(z_s_flat))
                    t_0 = tf.zeros(shape = tf.shape(z_s_flat))      

                    sign_z_flat = tf.where(z_s_flat >= 0, t_1, t_0) * 2 - 1
                    z_s_flat = tf.reshape(z_s, [-1]) + sign_z_flat * 1e-8
                    x_s_flat = tf.reshape(x_s, [-1]) / z_s_flat
                    y_s_flat = tf.reshape(y_s, [-1]) / z_s_flat

                    x_s = tf.reshape(x_s_flat, [num_batch, eh - sh + 1, ew - sw + 1])
                    y_s = tf.reshape(y_s_flat, [num_batch, eh - sh + 1, ew - sw + 1])
                    row_x_.append(x_s)
                    row_y_.append(y_s)
                row_x = tf.concat(row_x_, axis=2)
                row_y = tf.concat(row_y_, axis=2)
                x_.append(row_x)
                y_.append(row_y)

            x = tf.reshape(tf.concat(x_, axis=1), [num_batch, height, width, 1], name='x_map')
            y = tf.reshape(tf.concat(y_, axis=1), [num_batch, height, width, 1], name='y_map')
            print('================_transform3==================================')
            print('===============xy===========')
            print(x)
            print(y)

            img = tf.concat([x, y], axis=3)
            x_s_flat = tf.reshape(x, [-1])
            y_s_flat = tf.reshape(y, [-1])

            t_1 = tf.ones(shape = tf.shape(x_s_flat))
            t_0 = tf.zeros(shape = tf.shape(x_s_flat))    
            cond = tf.logical_or(tf.logical_or(tf.greater(t_1 * -1, x_s_flat), tf.greater(x_s_flat, t_1)), 
                                 tf.logical_or(tf.greater(t_1 * -1, y_s_flat), tf.greater(y_s_flat, t_1)))
            black_pix = tf.reshape(tf.where(cond, t_1, t_0), [num_batch, height, width], name='black_pix')
            #black_pix = tf.reduce_sum(black_pix, [1])

            out_size = (height, width)
            input_transformed = _interpolate(
                input_dim, x_s_flat, y_s_flat,
                out_size)

            output = tf.reshape(
                input_transformed, tf.stack([num_batch, height, width, num_channels]), name='output_img')
            
            print("!@#$%^===output/black_pix=======================")
            print(output)
            print(black_pix)
            print("!@#$%^==========================")
            return output, black_pix, img

    def _transform2(theta, input_dim):
        with tf.variable_scope('_transform'):
            num_batch = tf.shape(input_dim)[0]
            num_channels = tf.shape(input_dim)[3]
            theta = tf.cast(theta, 'float32')
            
            img = tf.image.resize_bilinear(theta, [height, width], align_corners=True)
            x_s_flat = tf.reshape(tf.slice(img, [0, 0, 0, 0], [-1, -1, -1, 1]), [-1])
            y_s_flat = tf.reshape(tf.slice(img, [0, 0, 0, 1], [-1, -1, -1, 1]), [-1])
            '''
            grid = _meshgrid(height, width)
            grid = tf.expand_dims(grid, 0)
            grid = tf.reshape(grid, [-1])
            grid = tf.tile(grid, tf.stack([num_batch]))
            grid = tf.reshape(grid, tf.stack([num_batch, 3, -1]))

            with tf.name_scope('get_xy'):
                for h in range(height):
                    with tf.name_scope('h_' + str(h)):
                        for w in range(grid_w):
                            with tf.name_scope('w_' + str(w)):
                                theta_ = tf.slice(theta, [0, h // (height // grid_h), w, 0], [-1, 1, 1, -1])
                                theta_ = tf.reshape(theta_, [-1, 3, 3])
                                grid_ = tf.slice(grid, [0, 0, h * width + w * (width // grid_w)], 
                                        [-1, -1, width // grid_w])
                                T_g_ = tf.matmul(theta_, grid_)
                                if ((h == 0) and (w == 0)):
                                    T_g = T_g_
                                else:
                                    T_g = tf.concat([T_g, T_g_], 2)

            x_s = tf.slice(T_g, [0, 0, 0], [-1, 1, -1])
            y_s = tf.slice(T_g, [0, 1, 0], [-1, 1, -1])
            z_s = tf.slice(T_g, [0, 2, 0], [-1, 1, -1])
 
            z_s_flat = tf.reshape(z_s, [-1])
            t_1 = tf.ones(shape = tf.shape(z_s_flat))
            t_0 = tf.zeros(shape = tf.shape(z_s_flat))      

            sign_z_flat = tf.where(z_s_flat >= 0, t_1, t_0) * 2 - 1
            z_s_flat = tf.reshape(z_s, [-1]) + sign_z_flat * 1e-8
            x_s_flat = tf.reshape(x_s, [-1]) / z_s_flat
            y_s_flat = tf.reshape(y_s, [-1]) / z_s_flat
            '''
            
            t_1 = tf.ones(shape = tf.shape(x_s_flat))
            t_0 = tf.zeros(shape = tf.shape(x_s_flat))    
            cond = tf.logical_or(tf.logical_or(tf.greater(t_1 * -1, x_s_flat), tf.greater(x_s_flat, t_1)), 
                                 tf.logical_or(tf.greater(t_1 * -1, y_s_flat), tf.greater(y_s_flat, t_1)))
            black_pix = tf.reshape(tf.where(cond, t_1, t_0), [num_batch, height, width])
            #black_pix = tf.reduce_sum(black_pix, [1])

            out_size = (height, width)
            input_transformed = _interpolate(
                input_dim, x_s_flat, y_s_flat,
                out_size)

            output = tf.reshape(
                input_transformed, tf.stack([num_batch, height, width, num_channels]))
            return output, black_pix, img
    with tf.variable_scope(name):
        #output = _transform(theta, U, out_size)
        output = _transform3(theta, U)
        return output


def interpolate(im, x, y, out_size, name='SpatialInterpolate', **kwargs):
    def _repeat(x, n_repeats):
        with tf.variable_scope('_repeat'):
            rep = tf.transpose(
                tf.expand_dims(tf.ones(shape=tf.stack([n_repeats, ])), 1), [1, 0])
            rep = tf.cast(rep, 'int32')
            x = tf.matmul(tf.reshape(x, (-1, 1)), rep)
            return tf.reshape(x, [-1])

    def _interpolate(im, x, y, out_size):
        with tf.variable_scope('_interpolate'):
            # constants
            num_batch = tf.shape(im)[0]
            height = tf.shape(im)[1]
            width = tf.shape(im)[2]
            channels = tf.shape(im)[3]

            x = tf.cast(x, 'float32')
            y = tf.cast(y, 'float32')
            height_f = tf.cast(height, 'float32')
            width_f = tf.cast(width, 'float32')
            out_height = out_size[0]
            out_width = out_size[1]
            zero = tf.zeros([], dtype='int32')
            max_y = tf.cast(tf.shape(im)[1] - 1, 'int32')
            max_x = tf.cast(tf.shape(im)[2] - 1, 'int32')

            # scale indices from [-1, 1] to [0, width/height]
            x = (x + 1.0)*(width_f) / 2.0
            y = (y + 1.0)*(height_f) / 2.0

            # do sampling
            x0 = tf.cast(tf.floor(x), 'int32')
            x1 = x0 + 1
            y0 = tf.cast(tf.floor(y), 'int32')
            y1 = y0 + 1

            x0 = tf.clip_by_value(x0, zero, max_x)
            x1 = tf.clip_by_value(x1, zero, max_x)
            y0 = tf.clip_by_value(y0, zero, max_y)
            y1 = tf.clip_by_value(y1, zero, max_y)
            dim2 = width
            dim1 = width*height
            base = _repeat(tf.range(num_batch)*dim1, out_height*out_width)
            base_y0 = base + y0*dim2
            base_y1 = base + y1*dim2
            idx_a = base_y0 + x0
            idx_b = base_y1 + x0
            idx_c = base_y0 + x1
            idx_d = base_y1 + x1

            # use indices to lookup pixels in the flat image and restore
            # channels dim
            im_flat = tf.reshape(im, tf.stack([-1, channels]))
            im_flat = tf.cast(im_flat, 'float32')
            Ia = tf.gather(im_flat, idx_a)
            Ib = tf.gather(im_flat, idx_b)
            Ic = tf.gather(im_flat, idx_c)
            Id = tf.gather(im_flat, idx_d)

            # and finally calculate interpolated values
            x0_f = tf.cast(x0, 'float32')
            x1_f = tf.cast(x1, 'float32')
            y0_f = tf.cast(y0, 'float32')
            y1_f = tf.cast(y1, 'float32')
            wa = tf.expand_dims(((x1_f-x) * (y1_f-y)), 1)
            wb = tf.expand_dims(((x1_f-x) * (y-y0_f)), 1)
            wc = tf.expand_dims(((x-x0_f) * (y1_f-y)), 1)
            wd = tf.expand_dims(((x-x0_f) * (y-y0_f)), 1)
            output = tf.add_n([wa*Ia, wb*Ib, wc*Ic, wd*Id])
            return output
    with tf.variable_scope(name):
        num_batch = tf.shape(im)[0]
        height = out_size[0]
        width = out_size[1]
        channels = tf.shape(im)[3]
        
        x_flat = tf.reshape(x, [-1])
        y_flat = tf.reshape(y, [-1])
        output_flat = _interpolate(im, x_flat, y_flat, out_size)
        output = tf.reshape(output_flat, [num_batch, height, width, channels])
        return output

def batch_transformer(U, thetas, out_size, name='BatchSpatialTransformer'):
    """Batch Spatial Transformer Layer

    Parameters
    ----------

    U : float
        tensor of inputs [num_batch,height,width,num_channels]
    thetas : float
        a set of transformations for each input [num_batch,num_transforms,6]
    out_size : int
        the size of the output [out_height,out_width]

    Returns: float
        Tensor of size [num_batch*num_transforms,out_height,out_width,num_channels]
    """
    with tf.variable_scope(name):
        num_batch, num_transforms = map(int, thetas.get_shape().as_list()[:2])
        indices = [[i]*num_transforms for i in xrange(num_batch)]
        input_repeated = tf.gather(U, tf.reshape(indices, [-1]))
        return transformer(input_repeated, thetas, out_size)
