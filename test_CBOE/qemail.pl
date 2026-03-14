#!/usr/bin/perl
#use strict;
use Getopt::Std;
use MIME::Lite;
use File::Basename;

my $datahead='
Dear customer,

';
my $databody='     Please see the attached report(s).';
my $datatail='

Kind regards,

Quod Financial Operations
----------------------------------------------------------------------------

If you have any questions or comments please contact us using email address:

Support@quodfinancial.com
or call us on +44 207 997 7030';

# process options
my (%opts, $msg);

getopts('of:t:c:s:d:h:', \%opts);
if (!keys %opts) {
#if ($opts{o}) {
    die "usage: qemail.pl [-f from] [-t to] [-c cc] [-s subject] [-d data] [-h html email] list of file(s) to be attached
    example: qemail.pl -t me\@myself.com toto.txt\n";
}
$opts{f} ||= "support\@quodfinancial.com";
$opts{s} ||= "from Quod Support";
$opts{d} ||= "$databody";

# construct and send email

if ($opts{h}) {
    open FILE, '<', "$opts{h}" or die "Couldn't open file: $!";
    $emailbody = do { local $/; <FILE> };
    close FILE;
    $msg = MIME::Lite->new(
        From    => $opts{f},
        "Reply-To" => $opts{f},
        "Return-Path" =>  $opts{f},
        To      => $opts{t},
        Cc      => $opts{c},
        Subject => $opts{s},
        Type    => 'text/html',
        Data    => $emailbody
    );
}
else {
    $emailbody = "$datahead $opts{d} $datatail";
    $msg = MIME::Lite->new(
        From    => $opts{f},
        "Reply-To" => $opts{f},
        "Return-Path" =>  $opts{f},
        To      => $opts{t},
        Cc      => $opts{c},
        Subject => $opts{s},
        Data    => $emailbody
    );
}

while (@ARGV) {
    my $filepath = shift @ARGV;
    my $filesize = -s $filepath;
    my $filename = basename($filepath);
    my $dirname = dirname($filepath);
    if ( $filesize >= 10000000 && $filename !~ /\.zip/ ) {
        `cd $dirname; zip $filename.zip $filename`;
        $filepath = $filepath.".zip"
    }
    $filesize = -s $filepath;
    $filesize =~ s/(?<=\d)(?=(?:\d\d\d)+\b)/,/g;
    print " attached $filepath: $filesize bytes \n";
    $msg->attach('Type' => 'application/octet-stream',
                 'Encoding' => 'base64',
                 'Path' => $filepath);
}

#$msg->send('smtp','10.22.8.66');
if ( $opts{s} =~ /DICTIONARY/ )
{
print "spam email will not be sent";
}
else
{
$msg->send;
print "email \"$opts{s}\" sent to $opts{t} and cc $opts{c} \n";
}
