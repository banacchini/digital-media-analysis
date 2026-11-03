| config                                     | status        |   convergence_code |   beta_has_bio |   var_sender |   var_receiver |     loglik | se_has_bio   |   time_s |
|:-------------------------------------------|:--------------|-------------------:|---------------:|-------------:|---------------:|-----------:|:-------------|---------:|
| lbfgs                                      | ok            |                  0 |         0.1328 |        7.751 |         0.5639 | -2.785e+04 |              |    2.973 |
| gradient_descent                           | ok            |                  0 |         0.1292 |        7.569 |         0.5563 | -2.785e+04 |              |   34.16  |
| gradient_descent {'delta_rel_conv': 1e-08} | ok            |                  0 |         0.1299 |        7.739 |         0.5597 | -2.785e+04 |              |   56.69  |
| lbfgs {'delta_rel_conv': 1e-08}            | not_converged |                  2 |         0.1304 |        7.77  |         0.5593 | -2.785e+04 |              |    5.028 |
