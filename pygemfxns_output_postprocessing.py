# -*- coding: utf-8 -*-
"""
Created on Mon Oct 16 09:04:46 2017

@author: David Rounce

pygemfxns_output.py is a list of functions that are used for post-processing the model results.  Specifically, these 
functions are meant to interact with the main model output to extract things like runoff, ELA, SLA, etc., which will
be specified by the user.  This allows the main script to run as quickly as possible and record only the minimum amount
of model results.
"""
import numpy as np
import pandas as pd 
import netCDF4 as nc
from time import strftime
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib as mpl
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.axes_grid1.inset_locator import zoomed_inset_axes
import pickle
import scipy
from scipy.spatial.distance import cdist
from scipy.spatial.distance import pdist, squareform
from scipy.optimize import curve_fit
from sklearn.gaussian_process import GaussianProcess
from sklearn.neighbors import NearestNeighbors

import pygem_input as input
import pygemfxns_modelsetup as modelsetup
import cartopy

option_plot_futuresim = 1
option_calc_nearestneighbor = 0
option_mb_shean_analysis = 0
option_geodeticMB_loadcompare = 0

#%%===== PLOT FUNCTIONS =============================================================================================
def plot_latlonvar(lons, lats, variable, rangelow, rangehigh, title, xlabel, ylabel, colormap, east, west, south, north, 
                   xtick=1, 
                   ytick=1, 
                   marker_size=2,
                   option_savefig=0, 
                   fig_fn='Samplefig_fn.png',
                   output_filepath = input.main_directory + '/../Output/'):
    """
    Plot a variable according to its latitude and longitude
    """
    # Create the projection
    ax = plt.axes(projection=cartopy.crs.PlateCarree())
    # Add country borders for reference
    ax.add_feature(cartopy.feature.BORDERS)
    # Set the extent
    ax.set_extent([east, west, south, north], cartopy.crs.PlateCarree())
    # Label title, x, and y axes
    plt.title(title)
    ax.set_xticks(np.arange(east,west+1,xtick), cartopy.crs.PlateCarree())
    ax.set_yticks(np.arange(south,north+1,ytick), cartopy.crs.PlateCarree())
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    # Plot the data 
    plt.scatter(lons, lats, s=marker_size, c=variable, cmap='RdBu', marker='o', edgecolor='black', linewidths=0.25)
    #  plotting x, y, size [s=__], color bar [c=__]
    plt.clim(rangelow,rangehigh)
    #  set the range of the color bar
    plt.colorbar(fraction=0.02, pad=0.04)
    #  fraction resizes the colorbar, pad is the space between the plot and colorbar
    if option_savefig == 1:
        plt.savefig(output_filepath + fig_fn)
    plt.show()

    

def plot_caloutput(data):
    """
    Plot maps and histograms of the calibration parameters to visualize results
    """
    # Set extent
    east = int(round(data['CenLon'].min())) - 1
    west = int(round(data['CenLon'].max())) + 1
    south = int(round(data['CenLat'].min())) - 1
    north = int(round(data['CenLat'].max())) + 1
    xtick = 1
    ytick = 1
    # Select relevant data
    lats = data['CenLat'][:]
    lons = data['CenLon'][:]
    precfactor = data['precfactor'][:]
    tempchange = data['tempchange'][:]
    ddfsnow = data['ddfsnow'][:]
    calround = data['calround'][:]
    massbal = data['MB_geodetic_mwea']
    # Plot regional maps
    plot_latlonvar(lons, lats, massbal, 'Geodetic mass balance [mwea]', 'longitude [deg]', 'latitude [deg]', east, west, 
               south, north, xtick, ytick)
    plot_latlonvar(lons, lats, precfactor, 'precipitation factor', 'longitude [deg]', 'latitude [deg]', east, west, 
                   south, north, xtick, ytick)
    plot_latlonvar(lons, lats, tempchange, 'Temperature bias [degC]', 'longitude [deg]', 'latitude [deg]', east, west, 
                   south, north, xtick, ytick)
    plot_latlonvar(lons, lats, ddfsnow, 'DDF_snow [m w.e. d-1 degC-1]', 'longitude [deg]', 'latitude [deg]', east, west, 
                   south, north, xtick, ytick)
    plot_latlonvar(lons, lats, calround, 'Calibration round', 'longitude [deg]', 'latitude [deg]', east, west, 
                   south, north, xtick, ytick)
    # Plot histograms
    data.hist(column='MB_difference_mwea', bins=50)
    plt.title('Mass Balance Difference [mwea]')
    data.hist(column='precfactor', bins=50)
    plt.title('Precipitation factor [-]')
    data.hist(column='tempchange', bins=50)
    plt.title('Temperature bias [degC]')
    data.hist(column='ddfsnow', bins=50)
    plt.title('DDFsnow [mwe d-1 degC-1]')
    plt.xticks(rotation=60)
    data.hist(column='calround', bins = [0.5, 1.5, 2.5, 3.5])
    plt.title('Calibration round')
    plt.xticks([1, 2, 3])


#%% ===== PLOTTING: Future simulations =====
if option_plot_futuresim == 1:
#    output = nc.Dataset(input.output_filepath + '/../Output/' + 'PyGEM_R15_MPI-ESM-LR_rcp26_2000_2100_20180519.nc')
    output = nc.Dataset(input.output_filepath + 'R15_finalsims/PyGEM_R15_MPI-ESM-LR_rcp26_2000_2100_20180519.nc')
    plot_label = 'Region 15'
    
    # Select relevant data
    main_glac_rgi = pd.DataFrame(output['glac_table'][:], columns=output['glac_table_header'][:])
    main_glac_rgi['RGIId'] = 'RGI60-' + main_glac_rgi['RGIId'].astype(str)
    lats = main_glac_rgi['CenLat']
    lons = main_glac_rgi['CenLon']
    dates = nc.num2date(output['time'][:], units=output['time'].units, calendar=output['time'].calendar).tolist()
    years = output['year'][:]
    years_plus1 = output['year_plus1'][:]
    massbal_total = output['massbaltotal_glac_monthly'][:]
    massbal_total_mwea = massbal_total.sum(axis=1)/(massbal_total.shape[1]/12)
    volume_glac_annual = output['volume_glac_annual'][:]
    volume_glac_annual[volume_glac_annual[:,0] == 0] = np.nan
    volume_glac_annualnorm = volume_glac_annual / volume_glac_annual[:,0][:,np.newaxis] * 100
    volume_reg_annual = output['volume_glac_annual'][:].sum(axis=0)
    volume_reg_annualnorm = volume_reg_annual / volume_reg_annual[0] * 100
    slr_reg_annual_mm = ((volume_reg_annual[0] - volume_reg_annual) * input.density_ice / input.density_water / input.area_ocean * 10**6)
    runoff_glac_monthly = output['runoff_glac_monthly'][:]
    runoff_reg_monthly = runoff_glac_monthly.mean(axis=0)
    acc_glac_monthly = output['acc_glac_monthly'][:]
    acc_reg_monthly = acc_glac_monthly.mean(axis=0)
    acc_reg_annual = np.sum(acc_reg_monthly.reshape(-1,12), axis=1)
    refreeze_glac_monthly = output['refreeze_glac_monthly'][:]
    refreeze_reg_monthly = refreeze_glac_monthly.mean(axis=0)
    refreeze_reg_annual = np.sum(refreeze_reg_monthly.reshape(-1,12), axis=1)
    melt_glac_monthly = output['melt_glac_monthly'][:]
    melt_reg_monthly = melt_glac_monthly.mean(axis=0)
    melt_reg_annual = np.sum(melt_reg_monthly.reshape(-1,12), axis=1)
    massbaltotal_glac_monthly = output['massbaltotal_glac_monthly'][:]
    massbaltotal_reg_monthly = massbaltotal_glac_monthly.mean(axis=0)
    massbaltotal_reg_annual = np.sum(massbaltotal_reg_monthly.reshape(-1,12), axis=1)
    
    # Plot: Regional volume change [%]
    plt.plot(years_plus1, volume_reg_annualnorm, label=plot_label)
    plt.ylabel('Regional volume change [%]')
    plt.xlim(2000,2101)
    plt.legend()
    plt.show()
    
    # Plot: Regional sea-level rise [mm]
    plt.plot(years_plus1, slr_reg_annual_mm, label=plot_label)
    plt.ylabel('Sea-level rise [mm]')
    plt.xlim(2000,2101)
    plt.legend()
    plt.show()
    
    # Plot: Regional specific mass balance rate [mwea]
    
    
    # Plot: Regional map of volume change by glacier
    volume_change_glac_perc = output['volume_glac_annual'][:][:,0]
    volume_change_glac_perc[volume_change_glac_perc > 0] = (
            (volume_glac_annual[volume_change_glac_perc > 0,-1] - volume_glac_annual[volume_change_glac_perc > 0, 0]) 
            / volume_glac_annual[volume_change_glac_perc > 0, 0] * 100)
#    volume_change_glac_perc[volume_glac_annual[:,0] == 0] = np.nan
    # Set extent
    east = int(round(lons.min())) - 1
    west = int(round(lons.max())) + 1
    south = int(round(lats.min())) - 1
    north = int(round(lats.max())) + 1
    xtick = 1
    ytick = 1
    # Plot regional maps
    plot_latlonvar(lons, lats, volume_change_glac_perc, -100, 100, 'Volume change from 2000 - 2100 [%]', 
                   'longitude [deg]', 'latitude [deg]', 'jet_r', east, west, south, north, xtick, ytick, marker_size=20)
    
    

#    plt.plot(dates, runoff_reg_monthly, label='Region 15')
#    plt.ylabel('Runoff [m3 / month]', size=15)
#    plt.legend()
#    plt.show()
#    #plt.plot(month, massbaltotal_reg_monthly, label='massbal_total')
#    #plt.plot(month, acc_reg_monthly, label='accumulation')
#    #plt.plot(month, refreeze_reg_monthly, label='refreeze')
#    #plt.plot(month, -1*melt_reg_monthly, label='melt')
#    #plt.ylabel('monthly regional mean [m.w.e.] / month')
#    #plt.legend()
#    #plt.show()
#    plt.plot(years, massbaltotal_reg_annual, label='massbal_total')
#    plt.plot(years, acc_reg_annual, label='accumulation')
#    plt.plot(years, refreeze_reg_annual, label='refreeze')
#    plt.plot(years, -1*melt_reg_annual, label='melt')
#    plt.ylabel('Region 15 annual mean [m.w.e.]', size=15)
#    plt.legend()
#    plt.show()
    


#%% ===== NEAREST NEIGHBOR MB MWEA PARAMETERS =====
if option_calc_nearestneighbor == 1:
    # Load csv
    ds = pd.read_csv(input.main_directory + '/../Output/calibration_R15_20180403_Opt02solutionspaceexpanding.csv', 
                     index_col='GlacNo')
    # Drop nan data to retain only glaciers with calibrated parameters
    ds_cal = ds.dropna()
    ds_cal_lonlat = ds_cal.loc[:,['CenLon','CenLat']].values
    
    # Set number of nearest neighbors
    n_nbrs = 20
    
    # Create dictionary between cal indices and all the glacier indices
    cal_dict = dict(zip(np.arange(0,ds_cal.shape[0]),ds_cal.index.values))
    # Add columns to pandas dataframe
    col_name_list = []
    for n in range(n_nbrs):
        col_name = 'nearidx_' + str(n+1)
        ds[col_name] = np.nan
        col_name_list.append(col_name)
    
    # Loop through each glacier and select the closest 10 glaciers
#    for glac in range(ds.shape[0]):
#    for glac in [325,326,327,328,329,330,331,332,333,334,336,337,338,339,340,342,343,344,345,346,347,348]:
#    for glac in [469, 470, 498, 502]:
    for glac in [1272, 1277, 1308,1309, 1310,1311,1312,1315,1316, 1317, 1318, 1319, 1320, 1441, 1446, 1449, 1450, 1481]:
        # Avoid applying this to any glaciers that already were optimized
        if ds.iloc[glac, :].isnull().values.any() == True:
            print(ds.loc[glac,'RGIId'])
            # Select the lon/lat of the glacier's center
            glac_lonlat = np.zeros((1,2))
            glac_lonlat[:] = ds.loc[glac,['CenLon','CenLat']].values
            # Append the lon/lat
            glac_lonlat_wcal = np.append(glac_lonlat, ds_cal_lonlat, axis=0)
            # Calculate nearest neighbors (set neighbors + 1 to account for itself)
            nbrs = NearestNeighbors(n_neighbors=n_nbrs+1, algorithm='brute').fit(glac_lonlat_wcal)
            distances_raw, indices_raw = nbrs.kneighbors(glac_lonlat_wcal)
            # Select glacier (row 0) and remove itself (col 0), so left with indices for nearest neighbors
            indices_raw2 = indices_raw[0,:][indices_raw[0,:] > 0] - 1
            indices = np.array([cal_dict[n] for n in indices_raw2])
            # Add indices to columns
            ds.loc[glac, col_name_list] = indices            
            
            mb_nbrs = ds.loc[indices,'MB_geodetic_mwea']
            mb_nbrs_mean = mb_nbrs.mean()
            mb_nbrs_std = mb_nbrs.std()
            print(mb_nbrs_mean, mb_nbrs_std)
    
    ## Export csv file
#    ds.to_csv(input.main_directory + '/../Calibration_datasets/calparams_R15_20180403_nnbridx.csv', index=False)
    

#%% ===== MASS BALANCE ANALYSIS =====
if option_mb_shean_analysis == 1:
    # Set parameters within this little batch script
    option_nearestneighbor_export = 0
    
    # Load csv
    ds = pd.read_csv(input.main_directory + '/../Output/calibration_R15_20180403_Opt02solutionspaceexpanding.csv', 
                     index_col='GlacNo')
    # Select data of interest
    data_all = ds[['RGIId', 'Area', 'CenLon', 'CenLat', 'mb_mwea', 'mb_mwea_sigma', 'lrgcm', 'lrglac', 'precfactor', 
                   'precgrad', 'ddfsnow', 'ddfice', 'tempsnow', 'tempchange']].copy()
    # Drop nan data to retain only glaciers with calibrated parameters
    data = data_all.dropna()
    
    # Compute statistics
    mb_mean = data['mb_mwea'].mean()
    mb_std = data['mb_mwea'].std()
    mb_95 = [mb_mean - 1.96 * mb_std, mb_mean + 1.96 * mb_std]
    # Remove data outside of 95% confidence bounds
    data_95 = data[(data['mb_mwea'] >= mb_95[0]) & (data['mb_mwea'] <= mb_95[1])]
    mb_1std = [mb_mean - 1 * mb_std, mb_mean + 1 * mb_std]
    # Remove data outside of 95% confidence bounds
    data_1std = data[(data['mb_mwea'] >= mb_1std[0]) & (data['mb_mwea'] <= mb_1std[1])]
    
    # Plot Glacier Area vs. MB
    plt.scatter(data['Area'], data['mb_mwea'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('MB 2000-2015 [mwea]', size=12)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.legend()
    plt.show()
    # Only 95% confidence
    plt.scatter(data_95['Area'], data_95['mb_mwea'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('MB 2000-2015 [mwea]', size=12)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.ylim(-3,1.5)
    plt.legend()
    plt.show()
    # Only 1 std
    plt.scatter(data_1std['Area'], data_1std['mb_mwea'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('MB 2000-2015 [mwea]', size=12)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.ylim(-3,1.5)
    plt.legend()
    plt.show()
    
    # Bar plot
    bins = np.array([0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 200])
    hist, bin_edges = np.histogram(data.Area,bins) # make the histogram
    fig, ax = plt.subplots()
    # Plot the histogram heights against integers on the x axis
    ax.bar(range(len(hist)),hist,width=1)
    # Set the tickets to the middle of the bars
    ax.set_xticks([i for i,j in enumerate(hist)])
    # Set the xticklabels to a string taht tells us what the bin edges were
    ax.set_xticklabels(['{} - {}'.format(bins[i],bins[i+1]) for i,j in enumerate(hist)], rotation=45)
    plt.show()
    
    # Compute max/min for the various bins
    mb = data_1std['mb_mwea']
    area = data_1std['Area']
    mb_envelope = np.zeros((bins.shape[0]-1,3))
    for n in range(bins.shape[0] - 1):
        mb_envelope[n,0] = bins[n+1]
        mb_subset = mb[(area > bins[n]) & (area <= bins[n+1])]
        mb_envelope[n,1] = mb_subset.min()
        mb_envelope[n,2] = mb_subset.max()
    
    
    # zoomed in
    plt.scatter(data['Area'], data['mb_mwea'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('MB 2000-2015 [mwea]', size=12)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.xlim(0.1,2)
    plt.legend()
    plt.show()
    
    # Plot Glacier Area vs. MB
    plt.scatter(data['mb_mwea'], data['Area'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Glacier area [km2]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
     # Plot Glacier Area vs. MB
    plt.scatter(data_95['mb_mwea'], data_95['Area'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Glacier area [km2]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.xlim(-3,1.75)
    plt.legend()
    plt.show()
    
    # Histogram of MB data
    plt.hist(data['mb_mwea'], bins=50)
    plt.show()
    
    
    main_glac_rgi = modelsetup.selectglaciersrgitable(rgi_glac_number='all')
    # Select calibration data from geodetic mass balance from David Shean
    main_glac_calmassbal = modelsetup.selectcalibrationdata(main_glac_rgi)
    # Concatenate massbal data to the main glacier
    main_glac_rgi = pd.concat([main_glac_rgi, main_glac_calmassbal], axis=1)
    # Drop those with nan values
    main_glac_calmassbal = main_glac_calmassbal.dropna()
    main_glac_rgi = main_glac_rgi.dropna()
    
    main_glac_rgi[['lrgcm', 'lrglac', 'precfactor', 'precgrad', 'ddfsnow', 'ddfice', 'tempsnow', 'tempchange']] = (
            data[['lrgcm', 'lrglac', 'precfactor', 'precgrad', 'ddfsnow', 'ddfice', 'tempsnow', 'tempchange']])
    # Mass balance versus various parameters
    # Median elevation
    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['Zmed'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Median Elevation [masl]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    # Elevation range
    main_glac_rgi['elev_range'] = main_glac_rgi['Zmax'] - main_glac_rgi['Zmin']
    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['elev_range'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Elevation range [m]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    plt.scatter(main_glac_rgi['Area'], main_glac_rgi['elev_range'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Elevation range [m]', size=12)
    plt.xlabel('Area [km2]', size=12)
    plt.legend()
    plt.show()
    # Length
    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['Lmax'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Length [m]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    # Slope
    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['Slope'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Slope [deg]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    # Aspect
    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['Aspect'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('Aspect [deg]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    plt.scatter(main_glac_rgi['Aspect'], main_glac_rgi['precfactor'], facecolors='none', edgecolors='black', label='Region 15')
    plt.ylabel('precfactor [-]', size=12)
    plt.xlabel('Aspect [deg]', size=12)
    plt.legend()
    plt.show()
    # tempchange
    # Line of best fit
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(main_glac_rgi['mb_mwea'], main_glac_rgi['tempchange'])
    xplot = np.arange(-3,1.5)
    line = slope*xplot+intercept
#    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['tempchange'], facecolors='none', edgecolors='black', label='Region 15')
    plt.plot(main_glac_rgi['mb_mwea'], main_glac_rgi['tempchange'], 'o', mfc='none', mec='black')
    plt.plot(xplot, line)
    plt.ylabel('tempchange [deg]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    # precfactor
    # Line of best fit
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(main_glac_rgi['mb_mwea'], main_glac_rgi['precfactor'])
    xplot = np.arange(-3,1.5)
    line = slope*xplot+intercept
#    plt.scatter(main_glac_rgi['mb_mwea'], main_glac_rgi['tempchange'], facecolors='none', edgecolors='black', label='Region 15')
    plt.plot(main_glac_rgi['mb_mwea'], main_glac_rgi['precfactor'], 'o', mfc='none', mec='black')
    plt.plot(xplot, line)
    plt.ylabel('precfactor [-]', size=12)
    plt.xlabel('MB 2000-2015 [mwea]', size=12)
    plt.legend()
    plt.show()
    
    # Relationship between model parameters and elevation?
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(main_glac_rgi['Zmed'], main_glac_rgi['tempchange'])
    xplot = np.arange(4000,6500)
    line = slope*xplot+intercept
    plt.plot(main_glac_rgi['Zmed'], main_glac_rgi['tempchange'], 'o', mfc='none', mec='black')
    plt.plot(xplot, line)
    plt.xlabel('Zmed [masl]', size=12)
    plt.ylabel('tempchange [degC]', size=12)
    plt.legend()
    plt.show()
    equation = 'tempchange = ' + str(round(slope,7)) + ' * Zmed + ' + str(round(intercept,5)) 
    print(equation, ' , R2 =', round(r_value**2,2))
    
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(main_glac_rgi['Zmed'], main_glac_rgi['precfactor'])
    xplot = np.arange(4000,6500)
    line = slope*xplot+intercept
    plt.plot(main_glac_rgi['Zmed'], main_glac_rgi['precfactor'], 'o', mfc='none', mec='black')
    plt.plot(xplot, line)
    plt.xlabel('Zmed [masl]', size=12)
    plt.ylabel('precfactor [-]', size=12)
    plt.legend()
    plt.show()
    equation = 'precfactor = ' + str(round(slope,7)) + ' * Zmed + ' + str(round(intercept,5)) 
    print(equation, ' , R2 =', round(r_value**2,2))
    
    slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(main_glac_rgi['Zmed'], main_glac_rgi['ddfsnow'])
    xplot = np.arange(4000,6500)
    line = slope*xplot+intercept
    plt.plot(main_glac_rgi['Zmed'], main_glac_rgi['ddfsnow'], 'o', mfc='none', mec='black')
    plt.plot(xplot, line)
    plt.xlabel('Zmed [masl]', size=12)
    plt.ylabel('ddfsnow [mwe d-1 degC-1]', size=12)
    plt.legend()
    plt.show()
    equation = 'ddfsnow = ' + str(round(slope,12)) + ' * Zmed + ' + str(round(intercept,5)) 
    print(equation, ' , R2 =', round(r_value**2,2))
    
## Old plot script
#    data_raw = pd.read_csv(input.main_directory + '/../DEMs/main_glac_rgi_OnlySheanMB.csv')
##    data = data_raw[(data_raw['Area']>5) & (data_raw['Area']<20)]
#    data = data_raw
#    lat = data['CenLat']
#    lon = data['CenLon']
#    area = data['Area']
#    mb = data['mb_mwea']
#    area4markers = area.copy()
#    area4markers[area > 0.1] = 10
##    area4markers[area > 1] = 20
#    area4markers[area > 5] = 100
#    area4markers[area > 20] = 300
##    area4markers = 100
#    # Plot Glacier Area vs. MB
#    plt.scatter(area, mb, facecolors='none', edgecolors='black', label='Region 15')
#    plt.ylabel('MB 2000-2015 [mwea]', size=12)
#    plt.xlabel('Glacier area [km2]', size=12)
#    plt.legend()
#    plt.show()
##    plt.savefig('test_fig.png')
#    # Plot spatial distribution of mass balance data    
#    # Set extent
#    east = int(round(lon.min())) - 1
#    west = int(round(lon.max())) + 1
#    south = int(round(lat.min())) - 1
#    north = int(round(lat.max())) + 1
#    
#    plot_latlonvar(lon, lat, mb, -1, 1, 'MB 2000-2015 [mwea]', 'longitude [deg]', 
#                   'latitude [deg]', 'jet_r', east, west, south, north,
#                   option_savefig=1, fig_fn='Samplefig_fn.png', marker_size=area4markers)
  


#%% ===== ALL GEODETIC MB DATA LOAD & COMPARE (Shean, Brun, Mauer) =====
if option_geodeticMB_loadcompare == 1:
    main_glac_rgi = modelsetup.selectglaciersrgitable()
    
    # Mass balance column name
    massbal_colname = 'mb_mwea'
    # Mass balance uncertainty column name
    massbal_uncertainty_colname = 'mb_mwea_sigma'
    # Mass balance date 1 column name
    massbal_time1 = 'year1'
    # Mass balance date 1 column name
    massbal_time2 = 'year2'
    # Mass balance tolerance [m w.e.a]
    massbal_tolerance = 0.1
    # Calibration optimization tolerance
    
    # SHEAN DATA
    # Import .csv file
    ds = pd.read_csv(input.cal_mb_filepath + input.cal_mb_filedict[input.rgi_regionsO1[0]])
    main_glac_calmassbal_shean = np.zeros((main_glac_rgi.shape[0],4))
    ds[input.rgi_O1Id_colname] = ((ds[input.cal_rgi_colname] % 1) * 10**5).round(0).astype(int) 
    ds_subset = ds[[input.rgi_O1Id_colname, input.massbal_colname, input.massbal_uncertainty_colname, 
                    input.massbal_time1, input.massbal_time2]].values
    rgi_O1Id = main_glac_rgi[input.rgi_O1Id_colname].values
    for glac in range(rgi_O1Id.shape[0]):
        try:
            # Grab the mass balance based on the RGIId Order 1 glacier number
            main_glac_calmassbal_shean[glac,:] = (
                    ds_subset[np.where(np.in1d(ds_subset[:,0],rgi_O1Id[glac])==True)[0][0],1:])
            #  np.in1d searches if there is a match in the first array with the second array provided and returns an
            #   array with same length as first array and True/False values. np.where then used to identify the index
            #   where there is a match, which is then used to select the massbalance value
            #  Use of numpy arrays for indexing and this matching approach is much faster than looping through; however,
            #   need the for loop because np.in1d does not order the values that match; hence, need to do it 1 at a time
        except:
            # If there is no mass balance data available for the glacier, then set as NaN
            main_glac_calmassbal_shean[glac,:] = np.empty(4)
            main_glac_calmassbal_shean[glac,:] = np.nan
    main_glac_calmassbal_shean = pd.DataFrame(main_glac_calmassbal_shean, 
                                             columns=[input.massbal_colname, input.massbal_uncertainty_colname, 
                                                      input.massbal_time1, input.massbal_time2])
    
    main_glac_rgi['Shean_MB_mwea'] = main_glac_calmassbal_shean[input.massbal_colname]
    main_glac_rgi['Shean_MB_mwea_sigma'] = main_glac_calmassbal_shean[input.massbal_uncertainty_colname]
    main_glac_rgi['Shean_MB_year1'] = main_glac_calmassbal_shean[input.massbal_time1]
    main_glac_rgi['Shean_MB_year2'] = main_glac_calmassbal_shean[input.massbal_time2]
        
    # BRUN DATA
    # Import .csv file
    # RGIId column name
    cal_rgi_colname = 'GLA_ID'
    ds_all_raw = pd.read_csv(input.cal_mb_filepath + 'Brun_Nature2017_MB_glacier-wide.csv')
    ds_all = ds_all_raw[ds_all_raw['Measured GLA area [percent]'] >= 60]
    # Subset glaciers based on region
    ds = ds_all[ds_all[cal_rgi_colname].values.astype(int) == input.rgi_regionsO1[0]].copy()
    ds[input.rgi_O1Id_colname] = ((ds[cal_rgi_colname] % 1) * 10**5).round(0).astype(int) 
    rgi_O1Id = main_glac_rgi[input.rgi_O1Id_colname].values
    ds_Id = ds[input.rgi_O1Id_colname].values
    main_glac_calmassbal_Brun = np.zeros((main_glac_rgi.shape[0],ds.shape[1]))
    
    for glac in range(rgi_O1Id.shape[0]):
        try:
            # Grab the mass balance based on the RGIId Order 1 glacier number
            main_glac_calmassbal_Brun[glac,:] = ds.iloc[np.where(np.in1d(ds_Id,rgi_O1Id[glac])==True)[0][0],:].values
            #  np.in1d searches if there is a match in the first array with the second array provided and returns an
            #   array with same length as first array and True/False values. np.where then used to identify the index
            #   where there is a match, which is then used to select the massbalance value
            #  Use of numpy arrays for indexing and this matching approach is much faster than looping through; however,
            #   need the for loop because np.in1d does not order the values that match; hence, need to do it 1 at a time
        except:
            # If there is no mass balance data available for the glacier, then set as NaN
            main_glac_calmassbal_Brun[glac,:] = np.empty(6)
            main_glac_calmassbal_Brun[glac,:] = np.nan
    main_glac_calmassbal_Brun = pd.DataFrame(main_glac_calmassbal_Brun, columns=ds.columns)
    
    main_glac_rgi['Brun_MB_mwea'] = main_glac_calmassbal_Brun['MB [m w.a a-1]']
    main_glac_rgi['Brun_Tot_GLA_area[km2]'] = main_glac_calmassbal_Brun['Tot_GLA_area [km2]']
    main_glac_rgi['Brun_GLA_area_measured[%]'] = main_glac_calmassbal_Brun['Measured GLA area [percent]']
    main_glac_rgi['Brun_MB_err[mwea]'] = main_glac_calmassbal_Brun['err. on MB [m w.e a-1]']
    
    # MAUER DATA
    cal_rgi_colname = 'id'
    # Import .csv file
    ds_all_raw = pd.read_csv(input.cal_mb_filepath + 'RupperMauer_GeodeticMassBalance_Himalayas_2000_2016.csv')
    ds_all = ds_all_raw[ds_all_raw['percentCov'] >= 60]
    # Subset glaciers based on region
    ds = ds_all[ds_all[cal_rgi_colname].values.astype(int) == input.rgi_regionsO1[0]].copy()
    ds[input.rgi_O1Id_colname] = ((ds[cal_rgi_colname] % 1) * 10**5).round(0).astype(int) 
    rgi_O1Id = main_glac_rgi[input.rgi_O1Id_colname].values
    ds_Id = ds[input.rgi_O1Id_colname].values
    main_glac_calmassbal_Mauer = np.zeros((main_glac_rgi.shape[0],ds.shape[1]))
    
    for glac in range(rgi_O1Id.shape[0]):
        try:
            # Grab the mass balance based on the RGIId Order 1 glacier number
            main_glac_calmassbal_Mauer[glac,:] = ds.iloc[np.where(np.in1d(ds_Id,rgi_O1Id[glac])==True)[0][0],:].values
            #  np.in1d searches if there is a match in the first array with the second array provided and returns an
            #   array with same length as first array and True/False values. np.where then used to identify the index
            #   where there is a match, which is then used to select the massbalance value
            #  Use of numpy arrays for indexing and this matching approach is much faster than looping through; however,
            #   need the for loop because np.in1d does not order the values that match; hence, need to do it 1 at a time
        except:
            # If there is no mass balance data available for the glacier, then set as NaN
            main_glac_calmassbal_Mauer[glac,:] = np.empty(ds.shape[1])
            main_glac_calmassbal_Mauer[glac,:] = np.nan
    main_glac_calmassbal_Mauer = pd.DataFrame(main_glac_calmassbal_Mauer, columns=ds.columns)
    
    main_glac_rgi['Mauer_MB_mwea'] = main_glac_calmassbal_Mauer['geoMassBal']
    main_glac_rgi['Mauer_MB_mwea_sigma'] = main_glac_calmassbal_Mauer['geoMassBalSig']
    main_glac_rgi['Mauer_GLA_area_measured[%]'] = main_glac_calmassbal_Mauer['percentCov']
    main_glac_rgi['Mauer_MB_year1'] = main_glac_calmassbal_Mauer['Year1']
    main_glac_rgi['Mauer_MB_year2'] = main_glac_calmassbal_Mauer['Year2']
    
    # Differences
    main_glac_rgi['Dif_Shean-Mauer[mwea]'] = (
            main_glac_calmassbal_shean[input.massbal_colname] - main_glac_calmassbal_Mauer['geoMassBal'])
    main_glac_rgi['Dif_Shean-Brun[mwea]'] = (
            main_glac_calmassbal_shean[input.massbal_colname] - main_glac_calmassbal_Brun['MB [m w.a a-1]'])
    main_glac_rgi['Dif_Mauer-Brun[mwea]'] = (
            main_glac_calmassbal_Mauer['geoMassBal'] - main_glac_calmassbal_Brun['MB [m w.a a-1]'])
    # Statistics
    print('# of MB [Shean]:',main_glac_calmassbal_shean.copy().dropna().shape[0])
    print('# of MB [Brun]:',main_glac_calmassbal_Brun.copy().dropna().shape[0])
    print('# of MB [Mauer]:',main_glac_calmassbal_Mauer.copy().dropna().shape[0])
    print('# same glaciers (All 3):',main_glac_rgi.copy().dropna().shape[0])      
    print('# same glaciers (Shean/Mauer):',main_glac_rgi['Dif_Shean-Mauer[mwea]'].copy().dropna().shape[0])
    print('# same glaciers (Shean/Brun)',main_glac_rgi['Dif_Shean-Brun[mwea]'].copy().dropna().shape[0])
    print('# same glaciers (Mauer/Brun)',main_glac_rgi['Dif_Mauer-Brun[mwea]'].copy().dropna().shape[0])
    print('Mean difference (Shean/Mauer):', main_glac_rgi['Dif_Shean-Mauer[mwea]'].mean())
    print('Min difference (Shean/Mauer):', main_glac_rgi['Dif_Shean-Mauer[mwea]'].min())
    print('Max difference (Shean/Mauer):', main_glac_rgi['Dif_Shean-Mauer[mwea]'].max())
    print('Mean difference (Shean/Brun):', main_glac_rgi['Dif_Shean-Brun[mwea]'].mean())
    print('Min difference (Shean/Brun):', main_glac_rgi['Dif_Shean-Brun[mwea]'].min())
    print('Max difference (Shean/Brun):', main_glac_rgi['Dif_Shean-Brun[mwea]'].max())
    print('Mean difference (Mauer/Brun):', main_glac_rgi['Dif_Mauer-Brun[mwea]'].mean())
    print('Min difference (Mauer/Brun):', main_glac_rgi['Dif_Mauer-Brun[mwea]'].min())
    print('Max difference (Mauer/Brun):', main_glac_rgi['Dif_Mauer-Brun[mwea]'].max())
    # Plot histograms of the differences
    plt.hist(main_glac_rgi['Dif_Shean-Mauer[mwea]'].copy().dropna().values)
    plt.xlabel('MB Shean - Mauer [mwea]', size=12)
    plt.show()
    plt.hist(main_glac_rgi['Dif_Shean-Brun[mwea]'].copy().dropna().values)
    plt.xlabel('MB Shean - Brun [mwea]', size=12)
    plt.show()
    plt.hist(main_glac_rgi['Dif_Mauer-Brun[mwea]'].copy().dropna().values)
    plt.xlabel('MB Mauer - Brun [mwea]', size=12)
    plt.show()
    # Plot differences vs. percent area
    #  Fairly consistent; only two 'outliers' 
    compare_shean_brun = (
            main_glac_rgi[['RGIId', 'Area', 'Dif_Shean-Brun[mwea]','Brun_GLA_area_measured[%]']].copy().dropna())
    compare_shean_mauer = (
            main_glac_rgi[['RGIId', 'Area', 'Dif_Shean-Mauer[mwea]','Mauer_GLA_area_measured[%]']].copy().dropna())
    plt.scatter(compare_shean_brun['Brun_GLA_area_measured[%]'].values, 
                compare_shean_brun['Dif_Shean-Brun[mwea]'].values)
    plt.xlabel('Brun % Glacier area measured', size=12)
    plt.ylabel('MB Shean - Brun [mwea]', size=12)
    plt.show()
    plt.scatter(compare_shean_brun['Area'].values, compare_shean_brun['Dif_Shean-Brun[mwea]'].values)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.ylabel('MB Shean - Brun [mwea]', size=12)
    plt.show()
    plt.scatter(compare_shean_mauer['Mauer_GLA_area_measured[%]'].values, 
                compare_shean_mauer['Dif_Shean-Mauer[mwea]'].values)
    plt.xlabel('Mauer % Glacier area measured', size=12)
    plt.ylabel('MB Shean - Mauer [mwea]', size=12)
    plt.show()
    plt.scatter(compare_shean_mauer['Area'].values, compare_shean_mauer['Dif_Shean-Mauer[mwea]'].values)
    plt.xlabel('Glacier area [km2]', size=12)
    plt.ylabel('MB Shean - Mauer [mwea]', size=12)
    plt.show()
    
    
#%% Envelope function
#    # Find envelope function
#    import statsmodels.formula.api as smf
#    data2 = data[['Area','mb_mwea']]
#    mod = smf.quantreg('mb_mwea ~ Area + I(Area ** 2.0)', data2)
#    res = mod.fit(q=0.5)
#    print(res.summary())
#    
#    quantiles = [0.01, 0.25, 0.50, 0.75, 0.99]
#    res_all = [mod.fit(q=q) for q in quantiles]
#    
#    res_ols = smf.ols('mb_mwea ~ Area + I(Area ** 2.0)', data2).fit()
#    
#    plt.figure()
#    
#    x_p = np.linspace(data2.Area.min(), data2.Area.max())
#    df_p = pd.DataFrame({'Area': x_p})
#    
#    for qm, res in zip(quantiles, res_all):
#        # get prediction from the model and plot
#        # here we use a dict which works the same way as the df in ols
#        plt.plot(x_p, res.predict({'Area': x_p}), linestyle='--', lw=1, color='k', label='q=%0.2F' % qm, zorder=2)
#    
#    y_ols_predicted = res_ols.predict(df_p)
#    plt.plot(x_p, y_ols_predicted, color='red', zorder=1)
#    #plt.scatter(df.temp, df.dens, alpha=.2)
#    plt.plot(data2.Area, data2.mb_mwea, 'o', alpha=.2, zorder=0)
#    plt.xlim((0.1, 80))
#    plt.ylim((-2, 4))
#    #plt.legend(loc="upper center")
#    plt.xlabel('Area [km2]')
#    plt.ylabel('MB [mwea]')
#    plt.title('')
#    plt.show()
    
#    # Logarythmic function
#    import statsmodels.formula.api as smf
#    data2 = data[['Area','mb_mwea']]
#    mod = smf.quantreg('mb_mwea ~ Area + I*np.log(Area) + I', data2)
#    res = mod.fit(q=0.5)
#    print(res.summary())
#    
#    quantiles = [0.01, 0.25, 0.50, 0.75, 0.99]
#    res_all = [mod.fit(q=q) for q in quantiles]
#    
#    res_ols = smf.ols('mb_mwea ~ Area + I*np.log(Area) + I', data2).fit()
#    
#    plt.figure()
#    
#    x_p = np.linspace(data2.Area.min(), data2.Area.max())
#    df_p = pd.DataFrame({'Area': x_p})
#    
#    for qm, res in zip(quantiles, res_all):
#        # get prediction from the model and plot
#        # here we use a dict which works the same way as the df in ols
#        plt.plot(x_p, res.predict({'Area': x_p}), linestyle='--', lw=1, color='k', label='q=%0.2F' % qm, zorder=2)
#    
#    y_ols_predicted = res_ols.predict(df_p)
#    plt.plot(x_p, y_ols_predicted, color='red', zorder=1)
#    #plt.scatter(df.temp, df.dens, alpha=.2)
#    plt.plot(data2.Area, data2.mb_mwea, 'o', alpha=.2, zorder=0)
#    plt.xlim((0.1, 80))
#    plt.ylim((-2, 4))
#    #plt.legend(loc="upper center")
#    plt.xlabel('Area [km2]')
#    plt.ylabel('MB [mwea]')
#    plt.title('')
#    plt.show()
    
    
##    # Exponential decay
##    def func(x, a, b, c):
##        return a * np.exp(-b * x) + c
##    popt, pcov = curve_fit(func, mb_max2[:,0], mb_max2[:,1])
##    y = func(A, popt[0], popt[1], popt[2])
#    
#    # Gaussian
#    def func(x, a, b, c):
#        return a * np.exp(-0.5 * (x - b)**2 / c**2)
#    popt, pcov = curve_fit(func, mb_max2[:,0], mb_max2[:,1])
#    y = func(A, popt[0], popt[1], popt[2])
#    plt.plot(mb_max2[:,0], mb_max2[:,1], 'o', mfc='none', mec='black')
#    plt.plot(A,y)
#    plt.plot()
#    plt.show()
    
    
#%%    # KRIGING
#    fig, ax = plt.subplots()
#    ax.scatter(data_95['CenLon'].values, data_95['CenLat'].values, c=data_95['tempchange'].values, cmap='RdBu')
#    ax.set_aspect(1)
#    ax.set_xlabel('Longitude [deg]')
#    ax.set_ylabel('Latitude [deg]')
#    ax.set_title('Temperature change')
#    
#    def SVh(P, h, bw):
#        "Experimental semivariogram for a single lag"
#        pd = squareform(pdist( P[:,:2]))
#        N = pd.shape[0]
#        Z = list()
#        for i in range(N):
#            for j in range(i+1, N):
#                if ((pd[i,j] >= h-bw) and (pd[i,j] <= h+bw)):
#                    Z.append((P[i,2] - P[j,2])**2.0)
#        svh = np.sum(Z) / (2 * len(Z))
#        return svh
#
#    def SV( P, hs, bw ):
#        "Experimental variogram for a collection of lags"
#        sv = list()
#        for h in hs:
#            sv.append( SVh( P, h, bw ) )
#        sv = [ [ hs[i], sv[i] ] for i in range( len( hs ) ) if sv[i] > 0 ]
#        return np.array( sv ).T     
#    
#    def covariancefxn(P, h, bw):
#        "Calculate the sill"
#        c0 = np.var(P[:,2])
#        if h == 0:
#            return c0
#        return c0 - SVh(P,h,bw)
#    
#    # Select x, y, and z data 
#    P = data_95[['CenLon', 'CenLat', 'tempchange']].values
#    # bandwidth +/- 250 m
#    bw = 0.025
#    # lags in 500 m increments from zero to 10,000
#    hs = np.arange(0,bw*10+1,bw)
#    # semivariogram
#    sv = SV(P, hs, bw )
#    # plot semivariogram
#    fig2, ax2 = plt.subplots()
#    plt.plot(sv[0], sv[1], '.-')
#    ax2.set_xlabel('Lag [deg]')
#    ax2.set_ylabel('Semivariance')
#    
#    # Steps to fit model to semivariogram
#    # Function to determine optimal parameter
#    def optModel(fct, x, y, C0, parameterRange=None, meshSize=1000 ):
#        if parameterRange == None:
#            parameterRange = [ x[1], x[-1] ]
##        print('parameter range:', parameterRange)
#        mse = np.zeros( meshSize )
##        print('mesh size:', meshSize)
#        a = np.linspace( parameterRange[0], parameterRange[1], meshSize )
##        print('size a:', a.shape)
#        for i in range( meshSize ):
##            print('i:', i)
##            print('y:', y)
##            print('a[i]:', a[i])
##            print('C0:', C0)
##            print('x:', x)
##            print('size x:', x.shape)
##            print('size y:', y.shape)
#            mse[i] = np.mean( ( y - fct( x, a[i], C0 ) )**2.0 )
#        return a[ mse.argmin() ]
#    # Spherical model
#    def spherical( h, a, C0 ):
#        "Spherical model of the semivariogram"
#        # if h is a single digit
#        if type(h) == np.float64:
#            # calculate the spherical function
#            if h <= a:
#                return C0*( 1.5*h/a - 0.5*(h/a)**3.0 )
#            else:
#                return C0
#        # if h is an iterable
#        else:
#            # calculate the spherical function for all elements
#            a = np.ones( h.size ) * a
#            C0 = np.ones( h.size ) * C0
#            return list(map( spherical, h, a, C0 ))
#        
#    # THIS WRAPS EVERYTHING TOGETHER
#    def cvmodel( P, model, hs, bw ):
#        """
#        Input:  (P)      ndarray, data
#                (model)  modeling function
#                          - spherical
#                          - exponential
#                          - gaussian
#                (hs)     distances
#                (bw)     bandwidth
#        Output: (covfct) function modeling the covariance
#        """
#        # calculate the semivariogram
#        sv = SV( P, hs, bw )
#        # calculate the sill
#        C0 = covariancefxn( P, hs[0], bw )
#        # calculate the optimal parameters
#        param = optModel( model, sv[0], sv[1], C0 )
#        # return a covariance function
##        covfct = lambda h: C0 - model( h, param, C0 )
#        covfct = lambda h: model(h,param,C0)
#        return covfct
#    
#    # Breakdown cvmodel into pieces
#    # Calculate the sill
#    C0 = covariancefxn( P, hs[0], bw )
#    # Calculate optimal parameter
#    param = optModel( spherical, sv[0], sv[1], C0 )
#    # Multiple ways of getting the covariance values
#    # Calculate values of spherical function
#    sp_values = np.zeros(sv.shape[1])
#    for i in range(sv.shape[1]):
#        sp_values[i] = spherical(sv[0,i], param, C0)
#    # Covariance function written out
##    sp = lambda h: spherical( h, param, C0 )
##    sp_values2 = sp(sv[0])
#    # Using the function does it all at once
#    sp = cvmodel( P, model=spherical, hs=np.arange(0,bw*10+1,bw), bw=0.025 )
#    
#    # plot semivariogram
#    fig3, ax3 = plt.subplots()
#    plt.plot(sv[0], sv[1], '.-')
#    plt.plot(sv[0], sp(sv[0]))
##    plt.plot(sv[0], sp2(sv[0]))
#    ax3.set_xlabel('Lag [deg]')
#    ax3.set_ylabel('Semivariance')
#    ax3.set_title('Spherical Model')
##    savefig('semivariogram_model.png',fmt='png',dpi=200)
#    
#    def krige( P, covfct, hs, bw, u, N ):
#        '''
#        Input  (P)     ndarray, data
#               (model) modeling function
#                        - spherical
#                        - exponential
#                        - gaussian
#               (hs)    kriging distances
#               (bw)    kriging bandwidth
#               (u)     unsampled point
#               (N)     number of neighboring
#                       points to consider
#        '''
#     
#        # covariance function
##        covfct = cvmodel( P, model, hs, bw )
#        # mean of the variable
#        mu = np.mean( P[:,2] )
#     
#        # distance between u and each data point in P
#        d = np.sqrt( ( P[:,0]-u[0] )**2.0 + ( P[:,1]-u[1] )**2.0 )
#        # add these distances to P
#        P = np.vstack(( P.T, d )).T
#        # sort P by these distances
#        # take the first N of them
#        P = P[d.argsort()[:N]]
#     
#        # apply the covariance model to the distances
#        k = covfct( P[:,3] )
#        # cast as a matrix
#        k = np.matrix( k ).T
#     
#        # form a matrix of distances between existing data points
#        K = squareform( pdist( P[:,:2] ) )
#        # apply the covariance model to these distances
#        K = covfct( K.ravel() )
#        # re-cast as a NumPy array -- thanks M.L.
#        K = np.array( K )
#        # reshape into an array
#        K = K.reshape(N,N)
#        # cast as a matrix
#        K = np.matrix( K )
#     
#        # calculate the kriging weights
#        weights = np.linalg.inv( K ) * k
#        weights = np.array( weights )
#     
#        # calculate the residuals
#        residuals = P[:,2] - mu
#     
#        # calculate the estimation
#        estimation = np.dot( weights.T, residuals ) + mu
#     
#        return float( estimation )
#
#    gridsize = [80, 100]
#    X0, X1 = P[:,0].min(), P[:,0].max()
#    Y0, Y1 = P[:,1].min(), P[:,1].max()
#    Z = np.zeros((gridsize[0],gridsize[1]))
#    dx, dy = (X1-X0)/gridsize[1], (Y1-Y0)/gridsize[0]
#    for i in range( gridsize[0] ):
#        if i%100 == 0:
#            print(i)
#        for j in range( gridsize[1] ):
#            Z[i,j] = krige( P, sp, hs, bw, (dy*j,dx*i), 16 )
#    # CURRENTLY RETURNS SAME VALUES EVERYWHERE!!


#    if option_nearestneighbor_export == 1:
#        # Select latitude and longitude of calibrated parameters for distance estimate
#        data_95_lonlat = data_95[['CenLon', 'CenLat']].values
#        # Loop through each glacier and select the parameters based on the nearest neighbor
#        for glac in range(data_all.shape[0]):
#            # Avoid applying this to any glaciers that already were optimized
#            if data_all.iloc[glac, :].isnull().values.any() == True:
#                # Select the latitude and longitude of the glacier's center
#                glac_lonlat = (data_all[['CenLon', 'CenLat']].values)[glac,:]
#                # Set point to be compatible with cdist function (from scipy)
#                pt = [[glac_lonlat[0],glac_lonlat[1]]]
#                # scipy function to calculate distance
#                distances = cdist(pt, data_95_lonlat)
#                # Find minimum index (could be more than one)
#                idx_min = np.where(distances == distances.min())[1]
#                # Set new parameters
#                data_all.iloc[glac,4:] = data_95.iloc[idx_min,4:].values.mean(0)
#                #  use mean in case multiple points are equidistant from the glacier
#        # Select only parameters to export to csv file
#        parameters_export = data_all.iloc[:,6:]
#        # Export csv file
#        parameters_export.to_csv(input.main_directory + 
#                                 '/../Calibration_datasets/calparams_R15_20180403_nearest_95confonly.csv', index=False)

#%%===== PLOTTING GRID SEARCH FOR A GLACIER ======
#data = nc.Dataset(input.main_directory + '/../Output/calibration_gridsearchcoarse_R15_20180324.nc', 'r+')
## Extract glacier information
#main_glac_rgi = pd.DataFrame(data['glacierinfo'][:], columns=data['glacierinfoheader'][:])
## Import calibration data for comparison
#main_glac_calmassbal = pd.read_csv(input.main_directory + '/../Output/R15_shean_geodeticmb_sorted.csv')
## Set glacier number
## Ngozumpa Glacier
#glac = 595
## Khumbu Glacier
##glac = 667
## Rongbuk Glacier
##glac = 1582
## East Rongbuk Glacier
##glac = 1607
#
## Select model parameters
#grid_modelparameters = data['grid_modelparameters'][:]
#precfactor = grid_modelparameters[:,2]
#tempchange = grid_modelparameters[:,7]
#ddfsnow = grid_modelparameters[:,4]
#precgrad = grid_modelparameters[:,3]
#ddfsnow_unique = np.unique(ddfsnow)
#precgrad_unique = np.unique(precgrad)
## Calculate mass balance and difference between modeled and measured
#massbaltotal_mwea = (data['massbaltotal_glac_monthly'][glac,:,:].sum(axis=1) / 
#    (main_glac_calmassbal.loc[glac,'year2'] - main_glac_calmassbal.loc[glac,'year1'] + 1))
#massbaltotal_mwea_cal = main_glac_calmassbal.loc[glac,'mb_mwea']
#difference = np.zeros((grid_modelparameters.shape[0],1))
#difference[:,0] = massbaltotal_mwea - massbaltotal_mwea_cal
#
#data_hist = np.concatenate((grid_modelparameters, difference), axis=1)
#data_hist = pd.DataFrame(data_hist, columns=['lrglac','lrgcm','precfactor','precgrad','ddfsnow','ddfice','tempsnow',
#                                             'tempchange','difference'])
## Plot histograms
##data_hist.hist(column='difference', bins=20)
##plt.title('Mass Balance Difference [mwea]')
#
## Plot map of calibration parameters
## setup the plot
#fig, ax = plt.subplots(1,1, figsize=(5,5))  
#markers = ['v','o','^']
#labels = ['0.0001', '0.0003', '0.0005']
## define the colormap
#cmap = plt.cm.jet_r
## extract all colors from the .jet map
#cmaplist = [cmap(i) for i in range(cmap.N)]
## create the new map
#cmap = cmap.from_list('Custom cmap', cmaplist, cmap.N)
## define the bins and normalize
#stepmin = -5
#stepmax = 6
#stepsize = 2
#bounds = np.arange(stepmin, stepmax, stepsize)
#norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
#for n in range(precgrad_unique.shape[0]):
#    precfactor_subset = precfactor[precgrad == precgrad_unique[n]]
#    if n == 0:
#        precfactor_subset = precfactor_subset - 0.05
#    elif n == 2:
#        precfactor_subset = precfactor_subset + 0.05
#    tempchange_subset = tempchange[precgrad == precgrad_unique[n]]
#    ddfsnow_subset = ddfsnow[precgrad == precgrad_unique[n]]
#    difference_subset = difference[precgrad == precgrad_unique[n]]
#    # Set size of markers based on DDFsnow
#    ddfsnow_norm = ddfsnow_subset.copy()
#    ddfsnow_norm[ddfsnow_subset == ddfsnow_unique[0]] = 10
#    ddfsnow_norm[ddfsnow_subset == ddfsnow_unique[1]] = 30
#    ddfsnow_norm[ddfsnow_subset == ddfsnow_unique[2]] = 50
#    ddfsnow_norm[ddfsnow_subset == ddfsnow_unique[3]] = 70
#    ddfsnow_norm[ddfsnow_subset == ddfsnow_unique[4]] = 90
#    # make the scatter
#    scat = ax.scatter(precfactor_subset, difference_subset, s=ddfsnow_norm, marker=markers[n], c=tempchange_subset, 
#                      cmap=cmap, norm=norm, label=labels[n])
## create the colorbar
#cb = plt.colorbar(scat, spacing='proportional', ticks=bounds)
##cb = plt.colorbar()
#tick_loc = bounds + stepsize/2
#cb.set_ticks(tick_loc)
#cb.set_ticklabels((bounds + stepsize/2).astype(int))
#cb.set_label('Tempchange [degC]')
##ax.set_title('TITLE')
#plt.xlabel('precfactor')
#plt.xlim((0.65, 1.85))
#plt.xticks([0.75, 1, 1.25, 1.5, 1.75])
#plt.ylabel('Difference [m w.e.a.]')
#plt.ylim((-2,2))
##plt.legend(loc=2)
#plt.show()
#fig.savefig(input.main_directory + '/../output/' + main_glac_rgi.loc[glac,'RGIID'] + '_gridsearch.png')
    

#%%===== PLOTTING ===========================================================================================
#netcdf_output15 = nc.Dataset(input.main_directory + 
#                              '/../Output/PyGEM_output_rgiregion15_ERAInterim_calSheanMB_nearest_20180306.nc', 'r+')
#netcdf_output15 = nc.Dataset(input.main_directory 
#                             + '/../Output/PyGEM_output_rgiregion15_ERAInterim_calSheanMB_nearest_20180403.nc', 'r+')
#netcdf_output14 = nc.Dataset(input.main_directory + 
#                             '/../Output/PyGEM_output_rgiregion14_ERAInterim_calSheanMB_nearest_20180313.nc', 'r+')
#netcdf_output14 = nc.Dataset(input.main_directory + 
#                             '/../Output/PyGEM_output_rgiregion14_ERAInterim_calSheanMB_transferAvg_20180313.nc', 'r+')

## Select relevant data
#glacier_data15 = pd.DataFrame(netcdf_output15['glacierparameter'][:])
#glacier_data15.columns = netcdf_output15['glacierparameters'][:]
#lats15 = glacier_data15['lat'].values.astype(float)
#lons15 = glacier_data15['lon'].values.astype(float)
#massbal_total15 = netcdf_output15['massbaltotal_glac_monthly'][:]
#massbal_total_mwea15 = massbal_total15.sum(axis=1)/(massbal_total15.shape[1]/12)
#volume_glac_annual15 = netcdf_output15['volume_glac_annual'][:]
#volume_reg_annual15 = volume_glac_annual15.sum(axis=0)
#volume_reg_annualnorm15 = volume_reg_annual15 / volume_reg_annual15[0]
#runoff_glac_monthly15 = netcdf_output15['runoff_glac_monthly'][:]
#runoff_reg_monthly15 = runoff_glac_monthly15.mean(axis=0)
#acc_glac_monthly15 = netcdf_output15['acc_glac_monthly'][:]
#acc_reg_monthly15 = acc_glac_monthly15.mean(axis=0)
#acc_reg_annual15 = np.sum(acc_reg_monthly15.reshape(-1,12), axis=1)
#refreeze_glac_monthly15 = netcdf_output15['refreeze_glac_monthly'][:]
#refreeze_reg_monthly15 = refreeze_glac_monthly15.mean(axis=0)
#refreeze_reg_annual15 = np.sum(refreeze_reg_monthly15.reshape(-1,12), axis=1)
#melt_glac_monthly15 = netcdf_output15['melt_glac_monthly'][:]
#melt_reg_monthly15 = melt_glac_monthly15.mean(axis=0)
#melt_reg_annual15 = np.sum(melt_reg_monthly15.reshape(-1,12), axis=1)
#massbaltotal_glac_monthly15 = netcdf_output15['massbaltotal_glac_monthly'][:]
#massbaltotal_reg_monthly15 = massbaltotal_glac_monthly15.mean(axis=0)
#massbaltotal_reg_annual15 = np.sum(massbaltotal_reg_monthly15.reshape(-1,12), axis=1)
##glacier_data14 = pd.DataFrame(netcdf_output14['glacierparameter'][:])
##glacier_data14.columns = netcdf_output14['glacierparameters'][:]
##lats14 = glacier_data14['lat'].values.astype(float)
##lons14 = glacier_data14['lon'].values.astype(float)
##massbal_total14 = netcdf_output14['massbaltotal_glac_monthly'][:]
##massbal_total_mwea14 = massbal_total14.sum(axis=1)/(massbal_total14.shape[1]/12)
##volume_glac_annual14 = netcdf_output14['volume_glac_annual'][:]
##volume_reg_annual14 = volume_glac_annual14.sum(axis=0)
##volume_reg_annualnorm14 = volume_reg_annual14 / volume_reg_annual14[0]
##runoff_glac_monthly14 = netcdf_output14['runoff_glac_monthly'][:]
##runoff_reg_monthly14 = runoff_glac_monthly14.mean(axis=0)
##acc_glac_monthly14 = netcdf_output14['acc_glac_monthly'][:]
##acc_reg_monthly14 = acc_glac_monthly14.mean(axis=0)
##acc_reg_annual14 = np.sum(acc_reg_monthly14.reshape(-1,12), axis=1)
##refreeze_glac_monthly14 = netcdf_output14['refreeze_glac_monthly'][:]
##refreeze_reg_monthly14 = refreeze_glac_monthly14.mean(axis=0)
##refreeze_reg_annual14 = np.sum(refreeze_reg_monthly14.reshape(-1,12), axis=1)
##melt_glac_monthly14 = netcdf_output14['melt_glac_monthly'][:]
##melt_reg_monthly14 = melt_glac_monthly14.mean(axis=0)
##melt_reg_annual14 = np.sum(melt_reg_monthly14.reshape(-1,12), axis=1)
##massbaltotal_glac_monthly14 = netcdf_output14['massbaltotal_glac_monthly'][:]
##massbaltotal_reg_monthly14 = massbaltotal_glac_monthly14.mean(axis=0)
##massbaltotal_reg_annual14 = np.sum(massbaltotal_reg_monthly14.reshape(-1,12), axis=1)
#years = np.arange(2000, 2016 + 1)
#month = np.arange(2000, 2016, 1/12)
#plt.plot(years,volume_reg_annualnorm15, label='Region 15')
##plt.plot(years,volume_reg_annualnorm14, label='Region 14')
#plt.ylabel('Volume normalized [-]', size=15)
#plt.legend()
#plt.show()
#plt.plot(month,runoff_reg_monthly15, label='Region 15')
#plt.ylabel('Runoff [m3 / month]', size=15)
#plt.legend()
#plt.show()
#plt.plot(month, massbaltotal_reg_monthly15, label='massbal_total')
#plt.plot(month, acc_reg_monthly15, label='accumulation')
#plt.plot(month, refreeze_reg_monthly15, label='refreeze')
#plt.plot(month, -1*melt_reg_monthly15, label='melt')
#plt.ylabel('monthly regional mean [m.w.e.] / month')
#plt.legend()
#plt.show()
#plt.plot(years[0:16], massbaltotal_reg_annual15, label='massbal_total')
#plt.plot(years[0:16], acc_reg_annual15, label='accumulation')
#plt.plot(years[0:16], refreeze_reg_annual15, label='refreeze')
#plt.plot(years[0:16], -1*melt_reg_annual15, label='melt')
#plt.ylabel('Region 15 annual mean [m.w.e.]', size=15)
#plt.legend()
#plt.show()
#
##lons = np.concatenate((lons14, lons15), axis=0)
##lats = np.concatenate((lats14, lats15), axis=0)
##massbal_total_mwea = np.concatenate((massbal_total_mwea14, massbal_total_mwea15), axis=0)
#lons = lons15
#lats = lats15
#massbal_total_mwea = massbal_total_mwea15
#
## Set extent
#east = int(round(lons.min())) - 1
#west = int(round(lons.max())) + 1
#south = int(round(lats.min())) - 1
#north = int(round(lats.max())) + 1
#xtick = 1
#ytick = 1
## Plot regional maps
#plot_latlonvar(lons, lats, massbal_total_mwea, -1.5, 0.5, 'Modeled mass balance [mwea]', 'longitude [deg]', 
#               'latitude [deg]', 'jet_r', east, west, south, north, xtick, ytick)

#%%### ====== PLOTTING FOR CALIBRATION FUNCTION ======================================================================
### Plot histograms and regional variations
##data13 = pd.read_csv(input.main_directory + '/../Output/calibration_R13_20180318_Opt01solutionspaceexpanding.csv')
##data13 = data13.dropna()
##data14 = pd.read_csv(input.main_directory + '/../Output/calibration_R14_20180313_Opt01solutionspaceexpanding.csv')
##data14 = data14.dropna()
##data15 = pd.read_csv(input.main_directory + '/../Output/calibration_R15_20180306_Opt01solutionspaceexpanding.csv')
#data15 = pd.read_csv(input.main_directory + '/../Output/calibration_R15_20180403_Opt02solutionspaceexpanding.csv')
#data15 = data15.dropna()
#data = data15
#
## Concatenate the data
##frames = [data13, data14, data15]
##data = pd.concat(frames)
#
### Fill in values with average 
### Subset all values that have data
##data_subset = data.dropna()
##data_subset_params = data_subset[['lrgcm','lrglac','precfactor','precgrad','ddfsnow','ddfice','tempsnow','tempchange']]
##data_subset_paramsavg = data_subset_params.mean()
##paramsfilled = data[['lrgcm','lrglac','precfactor','precgrad','ddfsnow','ddfice','tempsnow','tempchange']]
##paramsfilled = paramsfilled.fillna(data_subset_paramsavg)    
#
## Set extent
#east = int(round(data['CenLon'].min())) - 1
#west = int(round(data['CenLon'].max())) + 1
#south = int(round(data['CenLat'].min())) - 1
#north = int(round(data['CenLat'].max())) + 1
#xtick = 1
#ytick = 1
## Select relevant data
#lats = data['CenLat'][:]
#lons = data['CenLon'][:]
#precfactor = data['precfactor'][:]
#precgrad = data['precgrad'][:]
#tempchange = data['tempchange'][:]
#ddfsnow = data['ddfsnow'][:]
#calround = data['calround'][:]
#massbal = data['MB_geodetic_mwea']
#massbal_difference = data['MB_difference_mwea']
## Plot regional maps
#plot_latlonvar(lons, lats, massbal, -1.5, 0.5, 'Geodetic mass balance [mwea]', 'longitude [deg]', 'latitude [deg]', 
#               'RdBu', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, massbal_difference, 0, 0.15, 'abs(Mass balance difference) [mwea]', 'longitude [deg]', 
#               'latitude [deg]', 'jet_r', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, precfactor, 0.85, 1.3, 'Precipitation factor [-]', 'longitude [deg]', 'latitude [deg]', 
#               'jet_r', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, precgrad, 0.0001, 0.0002, 'Precipitation gradient [% m-1]', 'longitude [deg]', 'latitude [deg]', 
#               'jet_r', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, tempchange, -2, 2, 'Temperature bias [degC]', 'longitude [deg]', 'latitude [deg]', 
#               'jet', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, ddfsnow, 0.003, 0.005, 'DDF_snow [m w.e. d-1 degC-1]', 'longitude [deg]', 'latitude [deg]', 
#               'jet', east, west, south, north, xtick, ytick)
#plot_latlonvar(lons, lats, calround, 1, 3, 'Calibration round', 'longitude [deg]', 'latitude [deg]', 
#               'jet_r', east, west, south, north, xtick, ytick)
## Plot histograms
#data.hist(column='MB_difference_mwea', bins=50)
#plt.title('Mass Balance Difference [mwea]')
#data.hist(column='precfactor', bins=50)
#plt.title('Precipitation factor [-]')
#data.hist(column='precgrad', bins=50)
#plt.title('Precipitation gradient [% m-1]')
#data.hist(column='tempchange', bins=50)
#plt.title('Temperature bias [degC]')
#data.hist(column='ddfsnow', bins=50)
#plt.title('DDFsnow [mwe d-1 degC-1]')
#plt.xticks(rotation=60)
#data.hist(column='calround', bins = [0.5, 1.5, 2.5, 3.5])
#plt.title('Calibration round')
#plt.xticks([1, 2, 3])
#    
## run plot function
#output.plot_caloutput(data)


#%% ===== Plotting Anna =====
#output = nc.Dataset(input.main_directory + '/../Output/6.nc', 'r+')
#
### Select relevant data
#glacier_data = pd.DataFrame(output['glacierparameter'][:])
#glacier_data.columns = output['glacierparameters'][:]
#lats = glacier_data['lat'].values.astype(float)
#lons = glacier_data['lon'].values.astype(float)
#massbal_total = output['massbaltotal_glac_monthly'][:]
#massbal_total_mwea = massbal_total.sum(axis=1)/(massbal_total.shape[1]/12)
#
## Set extent
#east = int(round(lons.min())) - 1
#west = int(round(lons.max())) + 1
#south = int(round(lats.min())) - 1
#north = int(round(lats.max())) + 1
#xtick = 1
#ytick = 1
## Plot regional maps
#plot_latlonvar(lons, lats, massbal_total_mwea, -1.5, 0.5, 'Modeled mass balance [mwea]', 'longitude [deg]', 
#               'latitude [deg]', 'jet_r', east, west, south, north, xtick, ytick)