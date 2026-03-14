#!/bin/sh
export LD_LIBRARY_PATH=/usr/pgsql-16/lib:$LD_LIBRARY_PATH

# database end of day procedures #
export PGPASSWORD=$dbpassword
node1=`echo $dbhost | awk -F, '{print $1}'` ;
node2=`echo $dbhost | awk -F, '{print $2}'` ;
if [[ `/usr/bin/psql -h $node1 $dbconnect $dbuser -c "select pg_is_in_recovery();" -t | head -n 1;` == ' f' ]]; then
RUN_PSQL="/usr/bin/psql --set=sslmode=require -h $node1 $dbconnect $dbuserarchive -X --set ON_ERROR_STOP=on"
else
RUN_PSQL="/usr/bin/psql --set=sslmode=require -h $node2 $dbconnect $dbuserarchive -X --set ON_ERROR_STOP=on"
fi
${RUN_PSQL} <<EOF
CREATE TEMP VIEW VPT1 AS
with
Tradeinfo as (
select distinct execid from quod42adt.Execution where histcreationtime::date=CURRENT_DATE),
AllocInfo as (
select a2.allocinstructionid,a2.execid ,cgvp.venuecounterpartid  as GVPLEI,a.bookingtype as BookingType from quod42prd.allocinstruction a
left outer join quod42prd.allocinstructionexec a2 on (a.allocinstructionid=a2.allocinstructionid)
left outer join quod42prd.allocinstrctrpt ac on (a.allocinstructionid=ac.allocinstructionid and ac.partyrole ='GIV')
left outer join quod42prd.counterpartpartyrole cgvp on (cgvp.counterpartid=ac.counterpartid and cgvp.partyrole='INV')
WHERE a.alloctype='P'  and a.allocstatus='ACK')
select distinct
e.execid as QuodRefID,
ert.regulatorytradeid as TVI,
e.transid as QuodOrderID,
O.side as side,
e.execprice as price,
e.execqty as ExecQty,
asid.securityid as ISIN,
v.currency as Currency,
to_char(e.creationtime::TIMESTAMP,'HH24:MI:SS.MS') as ExecTime,
e.creationtime::DATE as ExecDate,
E.lastmkt as MICCODE,
case when(E.exectype='TRD') then 'NEW' when (E.exectype='COR') then 'MODIFIED' when (E.exectype='CAN') then 'CANCELLED' end as EventType,
case when (E.execorigin='E') then 'MARKET'  when (E.execorigin='M') then 'MANUAL' end as ExecType,
case when e.manualordercrossid is not null then 'CROSS' else 'CLOB' end as TradeSubType,
V.securityexchange as Lastmkt,
O.userid as UserID,
C1.venuecounterpartid as LIQProvider,
c.venuecounterpartid as CPTLEI,
ec.venuecounterpartid as contrafirm,
case when (ecr.venuecounterpartid is null) then ecrp.venuecounterpartid else ecr.venuecounterpartid end  as BrokerLEI,
ag.allocinstructionmisc0 as BOFIELD1,
ag.allocinstructionmisc1 as BOFIELD2,
ag.allocinstructionmisc2 as BOFIELD3,
ag.allocinstructionmisc3 as BOFIELD4,
ag.allocinstructionmisc4 as BOFIELD5,
ag.allocinstructionmisc5 as BOFIELD6,
ag.allocinstructionmisc6 as BOFIELD7,
ag.allocinstructionmisc7 as BOFIELD8,
ag.allocinstructionmisc8 as BOFIELD9,
ag.allocinstructionmisc9 as BOFIELD10,
bbgid.securityid as BloombergCode,
e.settldate::DATE as SettlDate,
ecross.transid as CrossOrdID,
AI.allocinstructionid as AllocInstructionID,
AI.BookingType as BookingType,
AI.GVPLEI  as GVPLEI,
d.deskname as DeskName,
i.institutionname  as Institution,
case when e.sourceaccountid ='TLM_Error'  and e.execactive ='Y' then 'Y' else null end as HouseFill,
case when e.sourceaccountid ='TLM_Error'  and e.execactive ='Y' then e.sourceaccountid else null end  as HouseFillAccount,
case when (o.accountgroupid = 'TLM_Error') then 'Y' else null end as ErrorTrade,
e.lastvenueordid as MarketOrderID,
e.venueexecid as MarketExecID
from quod42prd.execution e
inner join Tradeinfo Ti on (e.execid=ti.execid)
inner join quod42prd.ordr o on (o.ordid = e.transid  and o.side =e.side and E.exectype in ('TRD','COR','CAN','POS') and E.execqty>0 AND O.parentordid is null )
left outer join quod42prd.ordrlistings o2 on o.ordid = o2.ordid
left outer join quod42prd.listing v on v.instrumentid =E.instrumentid and v.listingid = o2.listingid
left outer join quod42prd.alternatesecurityid asid on (v.listingid=asid.listingid and asid.securityidsource ='ISI')
left outer join quod42prd.alternatesecurityid bbgid on (v.listingid=bbgid.listingid and bbgid.securityidsource ='BLM')
left outer join quod42prd.ordrcounterpart ocpt on (ocpt.ordid =o.ordid and ocpt.partyrole='CLI')
left outer join quod42prd.ordrcounterpart ocpt1 on (ocpt1.ordid =o.ordid and ocpt1.partyrole='LIQ')
left outer join quod42prd.counterpartpartyrole c on (c.counterpartid=ocpt.counterpartid and c.partyrole='CLI')
left outer join quod42prd.counterpartpartyrole c1 on (c1.counterpartid=ocpt1.counterpartid and c1.partyrole='LIQ')
left outer join quod42prd.accountgroup ag on (ag.accountgroupid=o.accountgroupid)
left outer join quod42prd.execctrpt ecpt on (e.execid=ecpt.execid and ecpt.partyrole='CNF')
left outer join quod42prd.virtualmarketexecution ve on (e.execid=ve.virtualexecid)
left outer join quod42prd.route r on (r.routeid=e.lastrouteid)
left outer join quod42prd.execregulatorytrade ert on (ve.marketexecid=ert.execid and ert.regulatorytradeidtype='TVI')
left outer join quod42prd.counterpartpartyrole ec on (ec.counterpartid=ecpt.counterpartid and ec.partyrole='CNF')
left outer join quod42prd.counterpartpartyrole ecr on (ecr.counterpartid=r.counterpartid and ecr.partyrole='INV')
left outer join quod42prd.counterpartpartyrole ecrp on (ecrp.counterpartid=ecpt.counterpartid and ecpt.partyrole='CNF' and ecrp.partyrole='INV')
left outer join quod42prd.execution ecross on (e.contraexecid = ecross.execid)
left outer join Allocinfo AI on (AI.execid=e.execid)
left outer join quod42prd.deskuserroles dag on (o.userid=dag.userid and dag.alive='Y')
left outer join quod42prd.desk d   on (dag.deskid =d.deskid)
left outer join quod42prd.location l   on (d.locationid =l.locationid)
left outer join quod42prd.zone z   on (l.zoneid=z.zoneid)
left outer join quod42prd.institution i   on (z.institutionid=i.institutionid)
WHERE  dag.deskid in (1200011)  order by exectime desc ;\copy (SELECT * from VPT1) TO '$LOG_DIR/IntradayReports/DEV_TLM_Executions_$(date +%Y%m%d_%H%M).csv' WITH DELIMITER ',' CSV HEADER;
DROP VIEW VPT1;
EOF

if [ "${SITEENV}" == 'prod' ] ; then
#qemail.pl -s "EOD TFSD EXECUTION DETAILS- $(date +"%Y-%m-%d %H:%M")" -t "informatique@tsaf-paris.com;ci.paris@tsaf-paris.com;compliance-risk@tsaf-paris.com" -c "hakkim.rasheed@quodfinancial.com"  $LOG_DIR/IntradayReports/TLM_Executions_$(date +%Y%m%d_%H%M).csv
#qemail.pl -s "EOD TSAF EXECUTION DETAILS- $(date +"%Y-%m-%d %H:%M")" -t "hakkim.rasheed@quodfinancial.com"  $LOG_DIR//IntradayReports/Executions_$(date +%Y%m%d_%H%M).csv
sftp sftptfsdprod@10.22.8.66:outgoing/TLM_EODFiles  <<< $'put /Logs/quod42/IntradayReports/TLM_Executions_*.csv'
mv $LOG_DIR/IntradayReports/TLM_Executions_* $LOG_DIR/IntradayReports/Archive
elif [ "${SITEENV}" == 'uat' ] ; then
qemail.pl -s "EOD TFSD EXECUTION DETAILS- $(date +"%Y-%m-%d %H:%M")" -t "hakkim.rasheed@quodfinancial.com"  $LOG_DIR/IntradayReports/TLM_Executions_$(date +%Y%m%d_%H%M).csv
sftp sftptfsduat@10.22.8.66:outgoing/TLM_EODFiles <<< $'put /Logs/quod42/IntradayReports/TLM_Executions_*.csv'
mv $LOG_DIR/IntradayReports/TLM_Executions_* $LOG_DIR/IntradayReports/Archive
elif [ "${SITEENV}" == 'dev' ] ; then
sftp sftptfsduat@10.22.8.66:outgoing/TLM_EODFiles <<< $'put /Logs/quod42/IntradayReports/DEV_TLM_Executions_*.csv'
mv $LOG_DIR/IntradayReports/TLM_Executions_* $LOG_DIR/IntradayReports/Archive
fi 
