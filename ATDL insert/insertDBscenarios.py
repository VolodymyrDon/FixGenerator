#!usrbinenv perl
#VERSION TO BE USED AFTER 148 - Modified to handle duplicates

use XMLDOM;
use GetoptStd;
use SysHostname;
use Socket;
use DataDumper;
use DBI;

use vars qw( $opt_f );
use vars qw( $opt_u );

#Parameters
my $dbname = $ENV{'dbconnect'};
my $dbvendor = $ENV{'dbvendor'};
my $host = $ENV{'dbhost'};
my $port = $ENV{'dbport'};
my $username = $ENV{'dbuser'};
my $password = $ENV{'dbpassword'};
my @xmlfilenames=@ARGV;
my %hash;


if( @xmlfilenames == 0) {
print You need at least one xml ATDL file provided by the brokern;
exit 0;
}

if ( $dbvendor eq postgresql ) {
#DB INITIATE
        $dbh = DBI - connect(dbiPgdbname=$dbname;host=$host;port=$port,
                            $username,
                            $password,
                            {AutoCommit = 1, RaiseError = 1}
                         ) or die $DBIerrstr;
} else {
        $dbh = DBI - connect(dbiOraclehost=$host;sid=$dbname,
                            $username,
                            $password,
                            {AutoCommit = 1, RaiseError = 1}
                         ) or die $DBIerrstr;
}

# Function to check if scenario exists
sub scenario_exists {
    my ($venuescenarioid, $externalscenarioid, $scenarioidentifier, $versionident, $scenario_version) = @_;
    
    my $sth;
    if ( $dbvendor eq postgresql ) {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenario WHERE venuescenarioid =  AND externalscenarioid =  AND scenarioidentifier =  AND venuescenarioversionid =  AND venuescenarioversionvalue = );
    } else {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenario WHERE venuescenarioid =  AND externalscenarioid =  AND scenarioidentifier =  AND venuescenarioversionid =  AND venuescenarioversionvalue = );
    }
    
    $sth-execute($venuescenarioid, $externalscenarioid, $scenarioidentifier, $versionident, $scenario_version);
    my $ref = $sth-fetchrow_hashref();
    return ($dbvendor eq postgresql)  $ref-{'count'}  0  $ref-{'COUNT'}  0;
}

# Function to get existing scenario ID
sub get_scenario_id {
    my ($venuescenarioid, $externalscenarioid, $scenarioidentifier, $versionident, $scenario_version) = @_;
    
    my $sth;
    if ( $dbvendor eq postgresql ) {
        $sth = $dbh-prepare(SELECT scenarioid FROM $username.scenario WHERE venuescenarioid =  AND externalscenarioid =  AND scenarioidentifier =  AND venuescenarioversionid =  AND venuescenarioversionvalue = );
    } else {
        $sth = $dbh-prepare(SELECT scenarioid FROM $username.scenario WHERE venuescenarioid =  AND externalscenarioid =  AND scenarioidentifier =  AND venuescenarioversionid =  AND venuescenarioversionvalue = );
    }
    
    $sth-execute($venuescenarioid, $externalscenarioid, $scenarioidentifier, $versionident, $scenario_version);
    my $ref = $sth-fetchrow_hashref();
    return ($dbvendor eq postgresql)  $ref-{'scenarioid'}  $ref-{'SCENARIOID'};
}

# Function to check if algopolicy exists for a scenario
sub algopolicy_exists {
    my ($scenarioid) = @_;
    
    my $sth;
    if ( $dbvendor eq postgresql ) {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.algopolicy WHERE scenarioid = );
    } else {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.algopolicy WHERE scenarioid = );
    }
    
    $sth-execute($scenarioid);
    my $ref = $sth-fetchrow_hashref();
    return ($dbvendor eq postgresql)  $ref-{'count'}  0  $ref-{'COUNT'}  0;
}

# Function to check if scenario parameter exists
sub scenario_parameter_exists {
    my ($scenarioid, $parametername) = @_;
    
    my $sth;
    if ( $dbvendor eq postgresql ) {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenarioparameter WHERE scenarioid =  AND scenarioparametername = );
    } else {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenarioparameter WHERE scenarioid =  AND scenarioparametername = );
    }
    
    $sth-execute($scenarioid, $parametername);
    my $ref = $sth-fetchrow_hashref();
    return ($dbvendor eq postgresql)  $ref-{'count'}  0  $ref-{'COUNT'}  0;
}

# Function to check if scenario parameter enum exists
sub scenario_parameter_enum_exists {
    my ($scenarioid, $parametername, $wirevalue) = @_;
    
    my $sth;
    if ( $dbvendor eq postgresql ) {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenarioparameterenum WHERE scenarioid =  AND scenarioparametername =  AND scenarioparameterenumvalue = );
    } else {
        $sth = $dbh-prepare(SELECT COUNT() as count FROM $username.scenarioparameterenum WHERE scenarioid =  AND scenarioparametername =  AND scenarioparameterenumvalue = );
    }
    
    $sth-execute($scenarioid, $parametername, $wirevalue);
    my $ref = $sth-fetchrow_hashref();
    return ($dbvendor eq postgresql)  $ref-{'count'}  0  $ref-{'COUNT'}  0;
}

for my $xmlfilename (@xmlfilenames){
#PARSE CONFIG AND INSERT IN ARRAY
open(SELECTEDCFG, $xmlfilename) or die could not open file reason $! n;

print Processing file $xmlfilename n;
print '-' x 40;print n;

my $parser = new XMLDOMParser;
my $parsed = $parser - parsefile($xmlfilename);

foreach my $first_parse ($parsed - getElementsByTagName(Strategies))
{
        $scenarioident = $first_parse - getAttribute(strategyIdentifierTag);
        $versionident = $first_parse - getAttribute(versionIdentifierTag);
}

# separate parsing Strategies tags to support merged files
foreach ( $parsed - getElementsByTagName(Strategies)){
#PARSE ALL SCENARIOS AND INSERT IN HASH
foreach ( $_ - getElementsByTagName(Strategy) )
{
my $uirep = $_ - getAttribute(uiRep);
my $scenario_version = $_ - getAttribute(version);
my $strategyname = $_ - getAttribute(name);
my $fixvaluestrategyname = $_ - getAttribute(wireValue);
my $providerID = $_ - getAttribute(providerID);

my $line=$_;
my $merged_name=$providerID $uirep,$fixvaluestrategyname,${providerID} ${uirep},${providerID}${strategyname},$scenario_version;
    for my $parameter_list ($line - getElementsByTagName('Parameter')) {
        my $parameter_name = $parameter_list - getAttribute(name);
        my $parameter_type = $parameter_list - getAttribute(xsitype);
        my $parameter_fixtag = $parameter_list - getAttribute(fixTag);
        my $parameter_required = $parameter_list - getAttribute(use);
                my $parameter_constvalue = $parameter_list - getAttribute(constValue);
                if ( $parameter_constvalue eq  ) {
             $visible = 'Y';
             $editable = 'Y'
                } else {
             $visible = 'N';
             $editable = 'N'
                }
        $hash{$merged_name}{$parameter_name,$parameter_type,$parameter_required,$parameter_fixtag,$parameter_constvalue,$visible,$editable}{} = $enumID;
        my $spu=1;
        for my $enum_list ($parameter_list - getElementsByTagName('EnumPair')) {
           my $enumID = $enum_list - getAttribute(enumID);
           my $wireValue = $enum_list - getAttribute(wireValue);
           $hash{$merged_name}{$parameter_name,$parameter_type,$parameter_required,$parameter_fixtag,$parameter_constvalue,$visible,$editable}{$enumID} = $enumID,$wireValue,$spu;
           $spu = $spu +1;
        }
    }

}
}



#DEBUG HASH
#print Dumper %hash;

if ( $dbvendor eq postgresql ) {
                #TAKE MAX SCENARIOD FROM DB
                 $myscenarioid;
                 $algopolicyid;
                my $sth = $dbh-prepare(SELECT case when max(scenarioid)1000 then 1000 else max(scenarioid) end as scenarioid FROM $username.scenario;);
                $sth-execute();
                        while(my $ref = $sth-fetchrow_hashref()) {
                        $myscenarioid=$ref-{'scenarioid'};
                }
                my $sth = $dbh-prepare(SELECT max(algopolicyid) as algopolicyid FROM $username.algopolicy;);
                $sth-execute();
                        while(my $ref = $sth-fetchrow_hashref()) {
                        $algopolicyid=$ref-{'algopolicyid'};
}

} else {
                #TAKE MAX SCENARIOD FROM DB
                 $myscenarioid;
                 $algopolicyid;
                my $sth = $dbh-prepare(SELECT case when max(scenarioid)1000 then 1000 else max(scenarioid) end as scenarioid FROM $username.scenario);
                $sth-execute();
                        while(my $ref = $sth-fetchrow_hashref()) {
                        $myscenarioid=$ref-{'SCENARIOID'};
                }
                my $sth = $dbh-prepare(SELECT max(algopolicyid) as algopolicyid FROM $username.algopolicy);
                $sth-execute();
                        while(my $ref = $sth-fetchrow_hashref()) {
                        $algopolicyid=$ref-{'ALGOPOLICYID'};
                }
}

#PARSE GENERATED HASH
foreach my $scenarioname (sort keys %hash) {

    #Insert in DB ScenarioID
    my @scenario_array = split(,, $scenarioname);
    my $new_uirep = $scenario_array[0];
    my $venuescenarioid = $scenario_array[1];
        my $new_strategyname= $scenario_array[2];
        my $new_externalscenarioid = $scenario_array[3];
        my $new_scenario_version = $scenario_array[4];

    print Processing scenario $new_uirepn;
    
    my $current_scenarioid;
    
    # Check if scenario already exists
    if (scenario_exists($venuescenarioid, $new_externalscenarioid, $scenarioident, $versionident, $new_scenario_version)) {
        print   Scenario already exists, skipping scenario insertn;
        $current_scenarioid = get_scenario_id($venuescenarioid, $new_externalscenarioid, $scenarioident, $versionident, $new_scenario_version);
    } else {
        #MAX SCENARIO ID FROM DB + 1
        $myscenarioid++;
        $current_scenarioid = $myscenarioid;
        
        #Insert new Scenario
        print   Inserting new scenarion;
        $sth = $dbh-prepare('INSERT INTO scenario (scenarioid, algotype, scenariogroupid, alive, scenariodesc, scenarioname, scenariotype, venuescenarioid, usecriteria, defaultexectraderctrptid, scenariocategoryenumid, clientscenarioid, pictureblobid, defaultordtype, defaulttif,defaultalgopolicyid, externalscenarioid, scenarioidentifier, venuescenarioversionid, venuescenarioversionvalue) VALUES (, , , , , , , , , , , , , , , , , , , )');
        $sth-execute($current_scenarioid,'EXT','2', 'Y', $new_uirep, $new_strategyname, 'BOTH', $venuescenarioid, 'N', undef, '1', $new_externalscenarioid, undef, undef, undef, $algopolicyid+1,$new_externalscenarioid, $scenarioident, $versionident,$new_scenario_version);
    }

    # Check if algopolicy already exists for this scenario
    if (algopolicy_exists($current_scenarioid)) {
        print   Algopolicy already exists for this scenario, skipping algopolicy insertn;
    } else {
        $algopolicyid++;
        print   Inserting new algopolicyn;
        #Insert new algopolicy
        $sth = $dbh-prepare('INSERT INTO algopolicy (algopolicyid, algopolicyname, algopolicydesc, clientalgopolicyid, venuealgopolicyid, pegged, defaulttif, alive, scenarioid, assetcategoryid, venueid, subvenueid, listinggroupid, instrumentgroupid, instrumentid, clientgroupid, accountgroupid, userid, roleid, deskid, defaultordtype) VALUES( , , , , , , , , , , , , , , , , , , , , )');
        $sth-execute($algopolicyid, 'Default', undef, undef, undef, undef, undef, 'Y', $current_scenarioid, undef, undef, undef, undef, undef, undef, undef, undef, undef, undef, undef, undef);
    }

    foreach my $parametername (keys %{ $hash{$scenarioname} }) {

        #Insert in DB ScenarioParamater
        my @parameter_array = split(,, $parametername);
        my $new_parametername = $parameter_array [0];
        my $parametertype = $parameter_array [1];
        my $parameterrequired = $parameter_array [2];
        my $parameterfixtag = $parameter_array [3];
        my $parameter_constvalue = $parameter_array [4];
        my $visible = $parameter_array [5];
        my $editable = $parameter_array [6];
        my $dbparametertype;

        ###########################
        #Scenario Parameter logic #
        ###########################
        if ( $parameterrequired eq required ) {
            $parameterrequired = Y;
        } else {
            $parameterrequired = N
        }

        if ( $parametertype =~ mUTCTimeOnly_t ) {
            $dbparametertype = H
        }

        if ( $parametertype =~ mUTCTimestamp_t ) {
            $dbparametertype = H
        }
		
        if ( $parametertype =~ mTZTimestamp_t ) {
            $dbparametertype = H
        }	

        if ( $parametertype =~ mTZTimeOnly_t ) {
            $dbparametertype = H
        }		

        if ( $parametertype =~ mBoolean_t ) {
            $dbparametertype = B
        }

        if ( $parametertype =~ mPrice_t ) {
            $dbparametertype = D
        }
		
        if ( $parametertype =~ mPriceOffset_t ) {
            $dbparametertype = D
        }

        if ( $parametertype =~ mInt_t ) {
            $dbparametertype = I
        }
		
		if ( $parametertype =~ mLength_t ) {
            $dbparametertype = I
        }

        if ( $parametertype =~ mQty_t ) {
            $dbparametertype = D
        }

        if ( $parametertype =~ mPercentage_t ) {
            $dbparametertype = D
        }

        if ( $parametertype =~ mChar_t ) {
            $dbparametertype = S
        }

        if ( $parametertype =~ mCurrency_t ) {
            $dbparametertype = S
        }
		
        if ( $parametertype =~ mExchange_t ) {
            $dbparametertype = S
        }

        if ( $parametertype =~ mTenor_t ) {
            $dbparametertype = S
        }
		
        if ( $parametertype =~ mString_t ) {
            $dbparametertype = S
        }
		
        if ( $parametertype =~ mAlgoPolicy_t ) {
            $dbparametertype = S
        }
		
        if ( $parametertype =~ mAlgoPolicyMap_t ) {
            $dbparametertype = S
        }

        if ( $parametertype =~ mAmt_t ) {
            $dbparametertype = D
        }
		
        if ( $parametertype =~ mFloat_t ) {
            $dbparametertype = D
        }
				
        if ( $parametertype =~ mUTCDateOnly_t ) {
            $dbparametertype = Y
        }
						
        if ( $parametertype =~ mLocalMktDate_t ) {
            $dbparametertype = Y
        }
		

        #Check number of enums in hash
        my $key_hash_number =  keys %{$hash{$scenarioname}{$parametername}};
        if ( $key_hash_number  1 ) {
            $dbparametertype = E
        }

        # Check if scenario parameter already exists
        if (scenario_parameter_exists($current_scenarioid, $new_parametername)) {
            print     Parameter '$new_parametername' already exists, skipping parameter insertn;
        } else {
            print     Inserting parameter '$new_parametername'n;
            my $sth = $dbh-prepare(INSERT INTO scenarioparameter(scenarioid, scenarioparametername, scenarioparametertype, scenarioparameterrequired, scenarioparameterdesc, scenarioparameterdefault, venuescenarioparameterid, scenarioparameterscope, isvisible, scenarioparameterindice, iseditable, alive) VALUES(, , , , , , , , , , , ));
            $sth-execute($current_scenarioid, $new_parametername, $dbparametertype, $parameterrequired, $new_parametername, $parameter_constvalue, $parameterfixtag, undef, $visible, undef, $editable, 'Y');
        }

        foreach my $enums (keys %{ $hash{$scenarioname}{$parametername} }) {
            my @enums_array = split(,, $hash{$scenarioname}{$parametername}{$enums});
            my $enum = $enums_array[0];
            my $wirevalue = $enums_array[1];
            my $indice = $enums_array[2];
            if ( $enums ne  && $enums !~ mNULL && $enums !~ mPleaseSelect) {
                # Check if scenario parameter enum already exists
                if (scenario_parameter_enum_exists($current_scenarioid, $new_parametername, $wirevalue)) {
                    print       Enum '$enum' already exists, skipping enum insertn;
                } else {
                    print       Inserting enum '$enum'n;
                    my $sth = $dbh-prepare(INSERT INTO scenarioparameterenum (scenarioid, scenarioparametername, scenarioparameterenumvalue, scenarioparameterenumname, scenarioparameterenumdesc, venuescenarioparamvalue, scenarioparameterenumindice) VALUES (,  , , , , , ));
                    $sth-execute($current_scenarioid, $new_parametername , $wirevalue, $enum, $enum, $wirevalue, $indice);
                }
            }
        }
    }
}
# clean hash, if not cleaned keeps previous scenarios, there must be a cleaner way, but this works for now
delete @hash{(keys %hash)};
print '-' x 40;print n;
}

# because we increase scenario ids manually we need to update sequences to match
print Running DBInstall 54 to update scenario id sequencesn;
my $db_path = $ENV{'DB_DIR'};
system(binbash $db_pathscriptsDBInstall.sh 54);
print '-' x 40;print n;
print Done.n;