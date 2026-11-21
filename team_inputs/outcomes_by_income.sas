libname data "~/Datathon/Data"; 
libname code "~/Datathon/Code";

/* Convert outcomes into long format */

ods pdf file="~/Datathon/Out/graphs.pdf";
ods select all;

data work.graph_data;
    set data.breast_analysis;
    
    if povcat24 <= 3 then lowinc = 1;
    else lowinc = 2;

    array outcomes {*} 
        CEFPHL42 CEFQLF42 CTRTMT42
        CFCARE42 CFNDBT42 CFNPMT42;

    array names[6] $10 _temporary_
        ('CEFPHL42', 'CEFQLF42', 'CTRTMT42',
         'CFCARE42', 'CFNDBT42', 'CFNPMT42');

    do i = 1 to dim(outcomes);

        outcome = names[i];
        response = strip(vvalue(outcomes[i]));

        if lowinc in (1,2) and outcomes[i] >= 0 and CSAQW24F > 0 then do;

            weight = CSAQW24F;
            output;
        end;

    end;

    keep lowinc outcome response weight;
run;

proc print data=graph_data(obs=10);
run;


/* Calculate weighted percentages */

proc summary data=work.graph_data nway;
    class outcome lowinc response;
    var weight;
    output out=work.graph_counts(drop=_TYPE_ _FREQ_)
        sum=weighted_n;
run;


/* Calculate percentages within each income group */

proc sql;
    create table work.graph_percent as
    select a.*,
           100 * a.weighted_n / b.total_weight
               as percentage

    from work.graph_counts as a

    inner join
    (
        select outcome, lowinc,
               sum(weighted_n) as total_weight
        from work.graph_counts
        group by outcome, lowinc
    ) as b

    on a.outcome = b.outcome
       and a.lowinc = b.lowinc;
quit;


/* Define graph labels */

proc format;
    value lowincf
        1 = "Low Income"
        2 = "Med to High Income";

    value $outlbl
        'CEFPHL42' = 'Physical Health'
        'CEFQLF42' = 'Quality of Life'
        'CTRTMT42' = 'Current Cancer Treatment'
        'CFCARE42' = 'Cancer Follow-up Care'
        'CFNDBT42' = 'Cancer-related Debt'
        'CFNPMT42' = 'Medical Bill Concerns';
run;

ods graphics on / width=10in height=5in;

proc sgpanel data=work.graph_percent;

    where outcome in ('CEFPHL42', 'CEFQLF42');

    panelby outcome /
        columns=2
        novarname
        spacing=12;

    styleattrs datacolors=(
        CX2878B5
        CX65A6A1
        CXE5B85C
        CXD47757
        CX795A8C
        CXA8A8A8
    );

    vbar lowinc /
        response=percentage
        group=response
        groupdisplay=stack
        stat=sum
        seglabel
        barwidth=0.65;

    colaxis label="Income Group"
        discreteorder=data;

    rowaxis label="Percentage of Respondents"
        values=(0 to 100 by 20)
        grid;

    keylegend / title="Response"
        position=bottom
        across=5;

    format lowinc lowincf.
           outcome $outlbl.;

    title "Health and Quality of Life by Income";

run;

proc sgpanel data=work.graph_percent;

    where outcome in ('CTRTMT42', 'CFCARE42');

    panelby outcome /
        columns=2
        novarname
        spacing=12;

    styleattrs datacolors=(
        CX2878B5
        CX65A6A1
        CXE5B85C
        CXD47757
        CX795A8C
    );

    vbar lowinc /
        response=percentage
        group=response
        groupdisplay=stack
        stat=sum
        seglabel
        barwidth=0.65;

    colaxis label="Income Group"
        discreteorder=data;

    rowaxis label="Percentage of Respondents"
        values=(0 to 100 by 20)
        grid;

    keylegend / title="Response"
        position=bottom
        across=5;

    format lowinc lowincf.
           outcome $outlbl.;

    title "Cancer Treatment and Follow-up Care by Income";

run;

proc sgpanel data=work.graph_percent;

    where outcome in ('CFNDBT42', 'CFNPMT42');

    panelby outcome /
        columns=2
        novarname
        spacing=12;

    styleattrs datacolors=(
        CX2878B5
        CX65A6A1
        CXE5B85C
        CXD47757
        CX795A8C
    );

    vbar lowinc /
        response=percentage
        group=response
        groupdisplay=stack
        stat=sum
        seglabel
        barwidth=0.65;

    colaxis label="Income Group"
        discreteorder=data;

    rowaxis label="Percentage of Respondents"
        values=(0 to 100 by 20)
        grid;

    keylegend / title="Response"
        position=bottom
        across=3;

    format lowinc lowincf.
           outcome $outlbl.;

    title "Cancer-related Financial Hardship by Income";

run;

ods graphics off;
ods pdf close;
run;

data work.test_data;
	if povcat24 <= 3 then lowinc = 1;
    else lowinc = 2;

    set data.breast_analysis;

    array outcomes {*} 
        CEFPHL42 CEFQLF42
        CTRTMT42 CFCARE42
        CFNDBT42 CFNPMT42;

    do i = 1 to dim(outcomes);
        if outcomes[i] < 0 then outcomes[i] = .;
    end;

    if lowinc not in (1,2) then delete;
    if CSAQW24F <= 0 then delete;

    drop i;
run;

proc surveyfreq data=work.test_data;
    strata VARSTR;
    cluster VARPSU;
    weight CSAQW24F;

    tables lowinc*CEFPHL42 / chisq row;
    tables lowinc*CEFQLF42 / chisq row;

    tables lowinc*CTRTMT42 / chisq row;
    tables lowinc*CFCARE42 / chisq row;

    tables lowinc*CFNDBT42 / chisq row;
    tables lowinc*CFNPMT42 / chisq row;

    title "Comparisons of Cancer Outcomes by Income Group";
run;