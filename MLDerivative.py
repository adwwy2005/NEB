import numpy as np
import scipy.optimize._minimize as spmin
import matplotlib.pyplot as plt

# Todo Blockwise inversion https://en.wikipedia.org/wiki/Invertible_matrix can be used for any matrix

class ML:
    """ Parent class for the surface fitting
    :param kernel is the mapping of the points to the feature space, kernel returns the pair distances of given points
                    and derivatives
    """
    def __init__(self, kernel):
        self.x_train = None
        self.x_prime_train = None
        self.y_train = None
        self.y_prime_train = None
        self.n_samples = None
        self.n_samples_prime = None
        self.n_dim = None

        self._is_fitted = False

        self.kernel = kernel

        self._intercept = None
        self._alpha = None
        self._support_index_alpha = None
        self._beta = None
        self._support_index_beta = None

    def _fit(self, x_train, y_train, x_prime_train=None, y_prime_train=None):
        """
        saves the necessary fitting data
        :param x_train: function input pattern  shape = [N_samples, N_features]
        :param y_train: function values to the pattern shape = [N_samples, 1]
        :param x_prime_train: derivative input pattern shape = [N_samples, N_features]
        :param y_prime_train: derivatives values shape = [N_samples, N_features]
        """
        self.x_train = x_train
        self.y_train = y_train
        self.x_prime_train = x_prime_train
        self.y_prime_train = y_prime_train

        self.n_samples = len(x_train)
        if y_prime_train is None:
            self.n_samples_prime = 0
            self.n_dim = len(x_train[0])
            self.y_prime_train = np.array([])
        else:
            self.n_samples_prime, self.n_dim = y_prime_train.shape

    def predict(self, x):
        """
        function value prediction method for a fitted model
        :param x: prediction pattern shape = [N_samples, N_features]
        :return: predicted function value
        """
        if self._is_fitted:
            if self.n_samples != 0 and self.n_samples_prime != 0:
                return self._alpha[self._support_index_alpha].dot(self.kernel(
                    self.x_train[self._support_index_alpha], x)) + sum(
                    self._beta[self._support_index_beta[ii], ii].dot(self.kernel(
                        self.x_prime_train[self._support_index_beta[ii]], x, ny=ii)) for ii in range(self.n_dim)) \
                       + self._intercept

            elif self.n_samples != 0:
                return self._alpha[self._support_index_alpha].dot(
                    self.kernel(self.x_train[self._support_index_alpha], x)) + self._intercept

            else:
                return sum(self._beta[self._support_index_beta[ii], ii].dot(self.kernel(
                    self.x_prime_train[self._support_index_beta[ii]], x, ny=ii)) for ii in range(self.n_dim))

        else:
            raise ValueError('not fitted yet')

    def predict_derivative(self, x):
        """
        derivative prediction for a fitted model
        :param x: prediction pattern shape = [N_samples, N_features]
        :return: derivative prediction
        """
        if self._is_fitted:
            ret_mat = np.zeros((len(x), self.n_dim))
            if self.n_samples_prime != 0 and self.n_samples != 0:
                for ii in range(self.n_dim):
                    ret_mat[:, ii] = self._alpha[self._support_index_alpha].dot(self.kernel(
                        self.x_train[self._support_index_alpha], x, nx=ii)) \
                                     + sum([self._beta[self._support_index_beta[jj], jj].dot(self.kernel(
                        self.x_prime_train[self._support_index_beta[jj]], x, nx=ii, ny=jj)) for jj in
                        range(self.n_dim)])

            elif self.n_samples != 0:
                for ii in range(self.n_dim):
                    ret_mat[:, ii] = self._alpha[self._support_index_alpha].dot(self.kernel(
                        self.x_train[self._support_index_alpha], x, nx=ii))

            else:
                for ii in range(self.n_dim):
                    ret_mat[:, ii] = sum([self._beta[self._support_index_beta[jj], jj].dot(self.kernel(
                        self.x_prime_train[self._support_index_beta[jj]], x, nx=ii, ny=jj)) for jj in
                        range(self.n_dim)])
            return ret_mat
        else:
            raise ValueError('not fitted yet')

    def predict_val_der(self, x):
        """
        function to allow to use the implemented NEB method
        :param x: prediction pattern, for derivative and function value the same shape = [N_samples, N_features]
        :return: function value prediction, derivative prediction
        """
        return self.predict(x), self.predict_derivative(x).reshape(-1)

    def _create_mat(self):
        """
        creates the matrix to the lagrangian
        See
        :return: matrix elements k, g, k_prime, j
        """
        # [[k, g]
        #  [k_prime,  j]]

        # k = np.zeros([self.n_samples, self.n_samples])
        # g_ = np.zeros([self.n_samples, self.n_samples_prime*self.n_dim])
        # k_prime_ = np.zeros([self.n_samples_prime*self.n_dim, self.n_samples])
        # j = np.zeros([self.n_samples_prime*self.n_dim, self.n_samples_prime*self.n_dim])

        if self.n_samples != 0:
            k = self._create_mat_part(self.x_train, self.x_train, dxy = 0)
            # mat = self.kernel(self.x_train, self.x_train)
            # k[:, :] = mat

        if self.n_samples_prime != 0:
            j = self._create_mat_part(self.x_prime_train, self.x_prime_train, dxy=2)
            # j = np.zeros([self.n_samples_prime * self.n_dim, self.n_samples_prime * self.n_dim])

            # for nx in range(0, self.n_dim):
            #     for ny in range(0, self.n_dim):
            #         ind_column = [ny * self.n_samples_prime, (ny + 1) * self.n_samples_prime]
            #         ind_row = [nx * self.n_samples_prime, (nx + 1) * self.n_samples_prime]
            #         mat = self.kernel(self.x_prime_train, self.x_prime_train, nx=nx, ny=ny)
            #         j[ind_column[0]:ind_column[1], ind_row[0]:ind_row[1]] = mat

        if self.n_samples != 0 and self.n_samples_prime != 0:
            g, k_prime = self._create_mat_part(self.x_train, self.x_prime_train, dxy=1)
        #     for dn in range(0, self.n_dim):
        #         ind1 = [dn * self.n_samples_prime, (dn + 1) * self.n_samples_prime]
        #         ind2 = [0, self.n_samples]
        #         g_[ind2[0]:ind2[1], ind1[0]:ind1[1]] = self.kernel(self.x_prime_train, self.x_train, nx=dn, ny=0)
        #         k_prime_[ind1[0]:ind1[1], ind2[0]:ind2[1]] = self.kernel(self.x_prime_train, self.x_train, nx=0, ny=dn)

        return k, g, k_prime, j

    def _create_mat_part(self, x, y, dxy=0):
        """
        creates parts of the matrix
        caution if dxy = 0 x, y are both function pattern
                if dxy = 1 x is function pattern and y is the prime pattern
                if dxy = 2 x, y are both the prime pattern
        :param x: first pattern
        :param y: second pattern
        :param dxy: determines which part is created. default: dxy=0 the simple kernel is created;
                                                               dxy=1 creates the first order derivative matrix
                                                               dxy=2 creates the second order derivative matrix
        :return: in case of dxy = 1 two matrix's are returned else just one
        """
        if dxy == 0:
            return self.kernel(x, y)

        elif dxy == 1:
            g = np.zeros([len(x), len(y)*len(y[0])])
            k_prime = np.zeros([len(y)*len(y[0]), len(x)])
            for ii in range(0, len(y[0])):
                ind1 = [ii * len(y), (ii + 1) * len(y)]
                ind2 = [0, len(x)]
                g[ind2[0]:ind2[1], ind1[0]:ind1[1]] = self.kernel(x, y, nx=ii, ny=0)
                k_prime[ind1[0]:ind1[1], ind2[0]:ind2[1]] = self.kernel(x, y, nx=0, ny=ii)
            return g, k_prime

        else:
            j = np.zeros([len(x)*len(x[0]), len(y)*len(y[0])])
            for ii in range(0, len(x[0])):
                for jj in range(0, len(y[0])):
                    ind_column = [jj * self.n_samples_prime, (jj + 1) * self.n_samples_prime]
                    ind_row = [ii * self.n_samples_prime, (ii + 1) * self.n_samples_prime]
                    j[ind_column[0]:ind_column[1], ind_row[0]:ind_row[1]] = self.kernel(x, y, nx=ii, ny=jj)
            return j

    def _invert_mat(self, mat):
        # mat = [[A B]      output = [[W X]
        #        [C D]]               [Y Z]]
        inv_mat = np.zeros(mat.shape)
        a = mat[:self.n_samples, :self.n_samples]
        b = mat[:self.n_samples, self.n_samples:]
        c = mat[self.n_samples:, :self.n_samples]
        d_inv = np.linalg.inv(mat[self.n_samples:, self.n_samples:])

        w = np.linalg.inv(a - b.dot(d_inv.dot(c)))
        x = -w.dot(b.dot(d_inv))

        inv_mat[:self.n_samples, :self.n_samples] = w
        inv_mat[:self.n_samples, self.n_samples:] = x
        inv_mat[self.n_samples:, :self.n_samples] = -d_inv.dot(c.dot(w))
        inv_mat[self.n_samples:, self.n_samples:] = d_inv + d_inv.dot(c.dot(w))

        return inv_mat


class IRWLS(ML):
    """
    Implementation of the iterative reweighed least square support vector machine for the simultaneous learning of the
    function value and derivatives
    See:
    """
    # Todo lagrangian function

    def fit(self, x_train, y_train, x_prime_train=None, y_prime_train=None, C1=1., C2=1., error_cap=10**-8, epsilon=0.01,
            max_iter=10**3, eps=10**-4):
        """
        Fit the model with given trainin data
        :param x_train: function input pattern shape = [N_samples, N_features]
        :param y_train: function values shape = [N_samples, 1]
        :param x_prime_train: derivative input pattern shape = [N_samples, N_features]
        :param y_prime_train: derivative values shape = [N_samples, N_features]
        :param C1: penalty parameter to the function error
        :param C2: penalty parameter to the derivative error
        :param error_cap: cuts the maximum function
        :param epsilon: parameter for the insensitive region around the curve
        :param max_iter: maximum iterations
        :param eps: used for convergence, if norm of the weights changes from on iteration to the next less than eps
        :return:
        """
        self._fit(x_train, y_train, x_prime_train=x_prime_train, y_prime_train=y_prime_train)
        self.y_prime_train = self.y_prime_train.flatten()
        k, g, k_prime, j = self._create_mat()

        a = np.zeros(self.n_samples * 2)
        s = np.zeros(self.n_samples_prime * self.n_dim * 2)

        a[1:self.n_samples:2] = C1
        a[self.n_samples::2] = C1
        s[1:self.n_samples_prime * self.n_dim:2] = C2
        s[self.n_samples_prime * self.n_dim::2] = C2

        support_index_alpha = np.arange(0, self.n_samples, 1)
        support_index_beta = np.arange(0, self.n_samples_prime * self.n_dim, 1)

        size_mat = self.n_samples + self.n_samples_prime * self.n_dim + 1
        mat = np.zeros([size_mat, size_mat])

        mat[:self.n_samples, :self.n_samples] = k
        mat[:self.n_samples, self.n_samples:-1] = g
        mat[self.n_samples:-1, :self.n_samples] = k_prime
        mat[self.n_samples:-1, self.n_samples:-1] = j
        mat[:self.n_samples, -1] = 1.
        mat[-1, :self.n_samples] = 1.

        step = 0
        converged = False
        alpha = np.zeros(self.n_samples)
        beta = np.zeros(self.n_samples_prime * self.n_dim)
        b = 0.

        alpha_old = 0
        beta_old = 0
        b_old = 0

        while not converged:

            index_a = np.logical_or(a[:self.n_samples] > 0., a[self.n_samples:] > 0.)
            index_s = np.logical_or(s[:self.n_samples_prime * self.n_dim] > 0., s[self.n_samples_prime * self.n_dim:] > 0.)

            a_ = a[:self.n_samples][index_a]
            a_star_ = a[self.n_samples:][index_a]
            s_ = s[:self.n_samples_prime * self.n_dim][index_s]
            s_star_ = s[self.n_samples_prime * self.n_dim:][index_s]

            self._support_index_alpha = support_index_alpha[index_a]
            self._support_index_beta = support_index_beta[index_s]

            n_support_alpha = len(self._support_index_alpha)
            n_support_beta = len(self._support_index_beta)

            d_a = (np.eye(n_support_alpha) / (a_ + a_star_))
            d_s = (np.eye(n_support_beta) / (s_ + s_star_))

            weight_index = np.concatenate([index_a, index_s, np.array([1])])

            index = np.logical_and(np.tile(weight_index, size_mat).reshape(size_mat, size_mat),
                                   np.tile(weight_index, size_mat).reshape(size_mat, size_mat).T)

            calc_mat = mat[index].reshape(n_support_alpha + n_support_beta + 1, n_support_alpha + n_support_beta + 1)

            if n_support_alpha == 0:
                # to avoid the singularity if just derivatives occur as support vectors
                calc_mat[-1, -1] = 1
                print('avoid singularity ' + str(step))

            calc_mat[:n_support_alpha, :n_support_alpha] += d_a
            calc_mat[n_support_alpha:-1, n_support_alpha:-1] += d_s

            target_vec = np.concatenate([self.y_train[self._support_index_alpha] + ((a_ - a_star_) / (a_ + a_star_)) * epsilon,
                                 self.y_prime_train.flatten()[self._support_index_beta] + ((s_ - s_star_) / (s_ + s_star_)) * epsilon,
                                 np.array([0])])

            weight = np.linalg.inv(calc_mat).dot(target_vec)

            alpha_s = np.zeros(self.n_samples)
            alpha_s[self._support_index_alpha] = weight[:n_support_alpha]
            beta_s = np.zeros(self.n_samples_prime * self.n_dim)
            beta_s[self._support_index_beta] = weight[n_support_alpha:-1]
            b_s = weight[-1]

            dir_alpha = alpha - alpha_s
            dir_beta = beta - beta_s
            dir_b = b - b_s

            f_error, g_error = self._error_function(alpha, beta, b, k, g, k_prime, j, epsilon)
            f_error_s, g_error_s = self._error_function(alpha_s, beta_s, b_s, k, g, k_prime, j, epsilon)

            f_s = np.logical_and(f_error < 0., f_error_s > 0.)
            g_s = np.logical_and(g_error < 0., g_error_s > 0.)
            eta = 1.
            if f_s.any() or g_s.any():
                eta = np.min(np.concatenate([f_error[f_s]/(f_error-f_error_s)[f_s], g_error[g_s]/(g_error-g_error_s)[g_s]]))

            alpha += dir_alpha * eta
            beta += dir_beta * eta
            b += dir_b * eta
            alpha = alpha_s.copy()
            beta = beta_s.copy()
            b = b_s

            f_error, g_error = self._error_function(alpha, beta, b, k, g, k_prime, j, epsilon)
            a = self._error_weight(f_error, C1, error_cap)
            s = self._error_weight(g_error, C2, error_cap)

            if step > 1:
                if np.linalg.norm(alpha - alpha_old) < eps and np.linalg.norm(beta-beta_old) < eps and\
                        abs(b-b_old) < eps:
                    converged = True
                    print('parameter converged ' + str(step))

            if step > max_iter:
                print('iteration is not converged ' + str(step))
                converged = True
            step += 1

            alpha_old = alpha.copy()
            beta_old = beta.copy()
            b_old = b

        self._alpha = alpha.copy()
        idx_beta = index_s.reshape(-1, self.n_dim)
        self._support_index_beta = []
        for ii in range(self.n_dim):
            self._support_index_beta.append(np.arange(0,self.n_samples_prime, 1)[idx_beta[:, ii]])
        self._beta = beta.copy().reshape(-1, self.n_dim)
        self._intercept = b
        self.y_prime_train = self.y_prime_train.reshape(-1,self.n_dim)
        self._is_fitted = True

    def _error_weight(self, error, constant, error_cap):
        """
        maximum error function with the cut at error_cap to avoid dividing by zero
        :param error:
        :param constant:
        :param error_cap:
        :return: error weights
        """
        weight = np.minimum(np.maximum(0., constant/error), constant/error_cap)
        return weight

    def _error_function(self, alpha, beta, b, k, g, k_prime, j, epsilon):
        """
        error calculation to the given training points in fit
        :return: function error, derivative error
        """
        func_error = np.zeros(self.n_samples * 2)
        grad_error = np.zeros(self.n_samples_prime * self.n_dim * 2)
        if self.n_samples != 0:
            func_prediction = alpha[self._support_index_alpha].dot(k[self._support_index_alpha, :]) +\
                              beta[self._support_index_beta].dot(k_prime[self._support_index_beta, :]) + b
            func_error[:self.n_samples] = func_prediction - self.y_train - epsilon
            func_error[self.n_samples:] = -func_prediction + self.y_train - epsilon
        if self.n_samples_prime != 0:
            grad_prediction = alpha[self._support_index_alpha].dot(g[self._support_index_alpha, :]) +\
                              beta[self._support_index_beta].dot(j[self._support_index_beta, :])
            grad_error[:self.n_samples_prime*self.n_dim] = grad_prediction - self.y_prime_train-epsilon
            grad_error[self.n_samples_prime * self.n_dim:] = -grad_prediction + self.y_prime_train - epsilon
        return func_error, grad_error

    def _lagrangian(self, alpha_, beta_, b_):
        pass


class RLS(ML):
    """
    Implementation of the regularized least square method for simultaneous fitting of function value and derivatives
    See:
    """

    def fit(self, x_train, y_train, x_prime_train=None, y_prime_train=None, minimze_b=False, C1=1., C2=1.):
        """
        Fitting a new model to a given training pattern
        :param x_train: function input pattern shape = [N_samples, N_features]
        :param y_train: function values shape = [N_samples, 1]
        :param x_prime_train: derivative input pattern shape = [N_samples, N_features]
        :param y_prime_train: derivative values shape = [N_samples, N_features]
        :param C1: penalty parameter to the function error
        :param C2: penalty parameter to the derivative error
        :param minimze_b: changes the behaviour to minimize the weights and the bias, default False minimizee only weights
        :return:
        """
        self._fit(x_train, y_train, x_prime_train=x_prime_train, y_prime_train=y_prime_train)

        k, g, k_prime, j = self._create_mat()

        if not minimze_b:
            mat_size = self.n_samples + self.n_samples_prime * self.n_dim + 1
            mat = np.zeros([mat_size, mat_size])
            mat[:self.n_samples, :self.n_samples] = k + np.eye(self.n_samples)*1/C1
            mat[:self.n_samples, self.n_samples:-1] = g
            mat[self.n_samples:-1, :self.n_samples] = k_prime
            mat[self.n_samples:-1, self.n_samples:-1] = j + np.eye(self.n_samples_prime*self.n_dim)*1/C2

            if self.n_samples == 0:
                mat[-1, -1] = 1
            else:
                mat[:self.n_samples, -1] = 1
                mat[-1, :self.n_samples] = 1
            # Todo implement inverting scheme
            vec = np.concatenate([self.y_train, self.y_prime_train.flatten(), np.zeros([1])])
            mat = np.linalg.inv(mat)

        else:
            vec = np.concatenate([self.y_train, self.y_prime_train.flatten()])
            mat_size = self.n_samples + self.n_samples_prime * self.n_dim
            mat = np.zeros([mat_size, mat_size])

            if self.n_dim == 1:
                # inverting matrix with the scheme for one dimension of the paper ..
                k = np.linalg.inv(k + 1)

                v = np.linalg.inv(j - k_prime.dot(k.dot(g)))
                u = -k.dot(g.dot(v))
                w = -v.dot(k_prime.dot(k))
                t = k - k.dot(g.dot(w))

                mat[:self.n_samples, :self.n_samples] = t
                mat[self.n_samples:, :self.n_samples] = w
                mat[:self.n_samples, self.n_samples:] = u
                mat[self.n_samples:, self.n_samples:] = v
            else:
                mat[:self.n_samples, :self.n_samples] = k
                mat[:self.n_samples, self.n_samples:-1] = g
                mat[self.n_samples:-1, :self.n_samples] = k_prime
                mat[self.n_samples:-1, self.n_samples:-1] = j
                mat = np.linalg.inv(mat)

        weight = mat.dot(vec)

        self._alpha = weight[0:self.n_samples].reshape(-1).T

        if not minimze_b:
            self._intercept = weight[-1]
            self._beta = weight[self.n_samples:-1].reshape(-1, self.n_dim)
        else:
            self._intercept = sum(self._alpha)
            self._beta = weight[self.n_samples:].reshape(-1, self.n_dim)

        self._support_index_alpha = np.arange(0, self.n_samples, 1)
        self._support_index_beta = []
        for ii in range(self.n_dim):
            self._support_index_beta.append(np.arange(0, self.n_samples_prime, 1))

        self._is_fitted = True


class GPR(ML):
    def fit(self, x_train, y_train, x_prime_train=None, y_prime_train=None, sigma_f=0.0, C1=None, C2=None):
        self._fit(x_train, y_train, x_prime_train=x_prime_train, y_prime_train=y_prime_train)
        # sigma_e, sigma_g = 10**-7, sigma_f = 1
        # covariance function = kernel
        # prior mean = K(x*,x)inv(K(x,x)+sigma**2)y_train
        noise = 10**-7
        self.sigma_f = sigma_f

        # initial energy value and gradient value
        prior_mean_y = np.mean(y_train)
        prior_mean_y_prime = np.mean(y_prime_train, axis=0)

        k, g, k_prime, j = self._create_mat()

        mat = np.zeros([self.n_samples + self.n_samples_prime * self.n_dim,
                        self.n_samples + self.n_samples_prime * self.n_dim])

        mat[:self.n_samples, :self.n_samples] = k + np.eye(self.n_samples) * noise
        mat[:self.n_samples, self.n_samples:] = g
        mat[self.n_samples:, :self.n_samples] = k_prime
        mat[self.n_samples:, self.n_samples:] = j + np.eye(self.n_samples_prime*self.n_dim) * noise

        weights = np.linalg.inv(mat).dot(np.concatenate([self.y_train-prior_mean_y,
                                                         self.y_prime_train.flatten()-prior_mean_y_prime]))
        self._alpha = weights[:self.n_samples]
        self._beta = weights[self.n_samples:].reshape(-1, self.n_dim)
        self._intercept = np.mean(prior_mean_y)

        self._support_index_alpha = np.arange(0, self.n_samples, 1)
        self._support_index_beta = []
        for ii in range(self.n_dim):
            self._support_index_beta.append(np.arange(0, self.n_samples_prime, 1))
        #
        self._is_fitted = True

    def covariance(self, x):
        k, g, k_prime, j = self._create_mat()

        mat = np.zeros([self.n_samples + self.n_samples_prime * self.n_dim,
                        self.n_samples + self.n_samples_prime * self.n_dim])

        mat[:self.n_samples, :self.n_samples] = k
        mat[:self.n_samples, self.n_samples:] = g
        mat[self.n_samples:, :self.n_samples] = k_prime
        mat[self.n_samples:, self.n_samples:] = j

        k_new = self._create_mat_part(x, x, dxy=0)
        g_new, k_prime_new = self._create_mat_part(x, self.x_train, dxy=1)
        # j_new = self._create_mat_part(x_prime, x_prime,dxy=2)

        mat_new = np.zeros([self.n_samples + self.n_dim*self.n_samples_prime, len(x)])

        mat_new[:self.n_samples] = self._create_mat_part(x, self.x_train)
        mat_new[self.n_samples:], dummy = self._create_mat_part(x, self.x_prime_train, dxy=1)
        # mat_new[:len(x), :len(x)] = k_new
        # mat_new[:len(x), len(x):] = g_new
        # mat_new[len(x):, :len(x)] = k_prime_new
        # mat_new[len(x):, len(x):] = j_new

        return sum(k_new - mat_new.T.dot(np.linalg.inv(mat).dot(mat_new)))
