import numpy as np
import pandas as pd
import random
import matplotlib.pyplot as plt
import matplotlib.transforms as mtrans
from lib import quantile_ied


def aleplot_1D_continuous(X, model, feature, grid_size=40):
    quantiles = np.append(0, np.arange(1 / grid_size, 1 + 1 / grid_size, 1 / grid_size))
    # use customized quantile function to get the same result as
    # type 1 R quantile (Inverse of empirical distribution function)
    bins = [X[feature].min()] + quantile_ied(X[feature], quantiles).to_list()
    bins = np.unique(bins)
    feat_cut = pd.cut(X[feature], bins, include_lowest=True)

    bin_codes = feat_cut.cat.codes
    bin_codes_unique = np.unique(bin_codes)

    X1 = X.copy()
    X2 = X.copy()
    X1[feature] = [bins[i] for i in bin_codes]
    X2[feature] = [bins[i + 1] for i in bin_codes]
    y_1 = model.predict(X1)
    y_2 = model.predict(X2)

    res_df = pd.DataFrame({"x": bins[bin_codes + 1], "Delta": y_2 - y_1})
    res_df = res_df.groupby(["x"]).Delta.agg(["size", ("eff", "mean")])
    res_df["eff"] = res_df["eff"].cumsum()
    res_df.loc[min(bins), :] = 0
    # subtract the total average of a moving average of size 2
    mean_mv_avg = (
        (res_df["eff"] + res_df["eff"].shift(1, fill_value=0)) / 2 * res_df["size"]
    ).sum() / res_df["size"].sum()
    res_df = res_df.sort_index().assign(eff=res_df["eff"] - mean_mv_avg)
    return res_df


def aleplot_1D_discrete(X, model, feature):
    groups = X[feature].unique()
    groups.sort()
    groups_codes = [x for x in range(len(groups))]

    groups_counts = X.groupby(feature).size()
    groups_props = groups_counts / sum(groups_counts)

    K = len(groups)

    # create copies of the dataframe
    X_plus = X.copy()
    X_neg = X.copy()
    # all groups except last one
    ind_plus = X[feature] < groups[K - 1]
    # all groups except first one
    ind_neg = X[feature] > groups[0]
    # replace once with one level up
    X_plus.loc[ind_plus, feature] = groups[X.loc[ind_plus, feature] + 1]
    # replace once with one level down
    X_neg.loc[ind_neg, feature] = groups[X.loc[ind_neg, feature] - 1]
    # predict with original and with the replaced values
    y_hat = model.predict(X)
    y_hat_plus = model.predict(X_plus[ind_plus])
    y_hat_neg = model.predict(X_neg[ind_neg])
    # compute prediction difference
    Delta_plus = y_hat_plus - y_hat[ind_plus]
    Delta_neg = y_hat[ind_neg] - y_hat_neg

    # compute the mean of the difference per group
    res_df = pd.concat(
        [
            pd.DataFrame({"Delta": Delta_plus, "x": X.loc[ind_plus, feature] + 1}),
            pd.DataFrame({"Delta": Delta_neg, "x": X.loc[ind_neg, feature]}),
        ]
    )
    res_df = res_df.groupby(["x"]).mean()
    res_df["eff"] = res_df["Delta"].cumsum()
    res_df.loc[0] = 0
    res_df = res_df.sort_index()
    res_df["eff"] = res_df["eff"] - sum(res_df["eff"] * groups_props)
    return res_df


def plot_1D_continuous_eff(ale_res):
    rug = [
        [ale_res.index[i]] * int(ale_res["size"].iloc[i])
        for i in range(ale_res.shape[0])
    ]
    rug = [x for y in rug for x in y]
    random.seed(123)
    rug = [
        sum(x) for x in zip(rug, [random.uniform(-0.05, 0.05) for x in range(len(rug))])
    ]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(ale_res[["eff"]])
    tr = mtrans.offset_copy(ax.transData, fig=fig, x=0.0, y=-5, units="points")
    ax.plot(
        rug,
        (ale_res[["eff"]].min()).to_list() * len(rug),
        "|",
        color="k",
        alpha=0.2,
        transform=tr,
    )
    return fig, ax
