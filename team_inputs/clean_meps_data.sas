/*****************************************************************************
* Project           : BioKind Datathon 2026
*
* Program name      : clean_meps_data.sas
*
* Author            : River Summers
*
* Last Edited       : 21Nov2026
*
* Purpose           : Consolidate and clean relevent MEPS breast cancer data. 
*****************************************************************************/

libname data "~/Datathon/Data"; 
libname code "~/Datathon/Code";

ods exclude EngineHost(persist);

data h2024;
	set data.h256;
run;

/* Keep only breast cancer conditions from HC-255 */

data work.breast_conditions;
    set data.h255
        (keep=DUPERSID ICD10CDX AGEDIAG);

    /* ICD-10-CM C50 = malignant neoplasm of breast */
    if substr(strip(ICD10CDX), 1, 3) = "C50";

    breast_c50_current = 1;
run;

/* One observation per person */
proc sort data=work.breast_conditions
          nodupkey;
    by DUPERSID;
run;

/* Keep relevant variables from HC-256 */

data work.person_data;
    set data.h256
        (keep=
            DUPERSID

            /* Breast cancer history */
            CABREAST CANCERDX CSAQELIG

            /* Demographics */
            AGE24X SEX RACETHX

            /* Socioeconomic status */
            FAMINC24 POVCAT24 POVLEV24

            /* Financial well-being */
            FWDEBT42 FWRENT42 FWCRED42
            FWUNEXP42 FWUTIL42

            /* Cancer-related financial hardship */
            CFNDBT42 CFNAMT42 CFNPMT42 CFNSTB42

            /* Treatment and follow-up */
            CDLTRT42 CDLFUP42 CDLVST42 CFCARE42
            CTRTMT42 CBCK42

            /* Quality of life */
            CEFPHL42 CEFMHL42 CEFQLF42
            CEFPIN42 CEFFTG42

            /* Healthcare expenditures */
            TOTEXP24 TOTSLF24

            /* Survey design */
            PERWT24F VARSTR VARPSU CSAQW24F
        );
run;


/* Merge breast cancer conditions with person-level data */

proc sql;
    create table work.breast_analysis as
    select
        a.*,
        coalesce(b.breast_c50_current, 0)
            as breast_c50_current

    from work.person_data as a

    left join work.breast_conditions as b
        on a.DUPERSID = b.DUPERSID

    /* Include people with either definition */
    where a.CABREAST = 1
       or b.breast_c50_current = 1;
quit;

data work.breast_analysis;
    set work.breast_analysis;

    array clean_vars {*} 
        AGE24X FAMINC24 POVCAT24 POVLEV24
        FWDEBT42 FWRENT42 FWCRED42
        FWUNEXP42 FWUTIL42
        CFNDBT42 CFNAMT42 CFNPMT42 CFNSTB42
        CDLTRT42 CDLFUP42 CDLVST42 CFCARE42
        CTRTMT42 CBCK42
        CEFPHL42 CEFMHL42 CEFQLF42
        CEFPIN42 CEFFTG42
        TOTEXP24 TOTSLF24;

    do i = 1 to dim(clean_vars);
        if clean_vars{i} in (-1, -7, -8, -15)
            then clean_vars{i} = .;
    end;

    drop i;
run;

/* Number of observations and variables */
proc contents data=work.breast_analysis;
run;

/* Number of respondents */
proc sql;
    select count(*) as Total_Respondents
    from work.breast_analysis;
quit;

/* Compare breast cancer identification methods */
proc freq data=work.breast_analysis;
    tables CABREAST*breast_c50_current / missing;
run;

/* Examine socioeconomic variables */
proc means data=work.breast_analysis
    n mean median std min max;
    var FAMINC24 POVLEV24 TOTEXP24 TOTSLF24;
run;

/* Examine financial hardship and treatment delays */
proc freq data=work.breast_analysis;
    tables CFNDBT42 CDLTRT42 CDLFUP42
           CFCARE42 CTRTMT42 CBCK42 / missing;
run;

proc export data=breast_analysis
    outfile="~/Datathon/Data/breast_analysis.csv"
    dbms=csv
    replace;
run;
	
