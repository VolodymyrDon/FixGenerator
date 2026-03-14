#!/usr/bin/bash
#------------------------------------------------------------------------------#
# Main                                                                         #
#------------------------------------------------------------------------------#

case "${1}" in
    "-b")
        java net.java.javafx.FXShell com.net2s.fs.midas.common.utils.mipbuilder.Mip
    ;;

    "-l")
        java com.net2s.fs.midas.common.utils.mipbuilder.MipToolsCmd --type UM --subject $2 --LOG --file $3
    ;;

    "-s")
        java com.net2s.fs.midas.common.utils.mipbuilder.MipToolsCmd --type UM --subject $2 --replysubject $3 --file ./$4 --lotsize 1 --interval 1 --count 1
    ;;

    "-m")
        java com.net2s.fs.midas.common.utils.mipbuilder.MipToolsCmd --type UM --subject $2 --file $3 --lotsize 1 --interval 1 --count 1
    ;;
esac
