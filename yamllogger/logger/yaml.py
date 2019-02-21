import yamllogger
import time
import hashlib

from morituri.common import common
from morituri.configure import configure
from morituri.result import result


class YamlLogger(result.Logger):

    _accuratelyRipped = 0
    _inARDatabase = 0
    _errors = False

    def log(self, ripResult, epoch=time.time()):
        """Returns big str: logfile joined text lines"""

        lines = self.logRip(ripResult, epoch=epoch)
        return "\n".join(lines)

    def logRip(self, ripResult, epoch):
        """Returns logfile lines list"""

        lines = []

        # Ripper version
        lines.append("Log created by: morituri %s (yaml logger %s)" % (
                     configure.version, yamllogger.__version__))

        # Rip date
        date = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch)).strip()
        lines.append("Log creation date: %s" % date)
        lines.append("")

        # Rip technical settings
        lines.append("Ripping phase information:")
        lines.append("  Drive: %s%s (revision %s)" % (
            ripResult.vendor, ripResult.model, ripResult.release))
        lines.append("  Extraction engine: cdparanoia %s" %
                     ripResult.cdparanoiaVersion)
        if ripResult.cdparanoiaDefeatsCache is None:
            defeat = "Unknown"
        elif ripResult.cdparanoiaDefeatsCache:
            defeat = "Yes"
        else:
            defeat = "No"
        lines.append("  Defeat audio cache: %s" % defeat)
        lines.append("  Read offset correction: %+d" % ripResult.offset)
        # Unsupported by both the official cdparanoia package and morituri
        # Feature implemented in whipper
        lines.append("  Overread into lead-out: No "
                     "(unsupported in morituri)")
        # Next one fully works only using the patched cdparanoia package
        # lines.append("Fill up missing offset samples with silence: Yes")
        lines.append("  Gap detection: cdrdao %s" % ripResult.cdrdaoVersion)
        # CD-R Detection (only implemented in whipper)
        lines.append("  CD-R detected: Unknown (unsupported in morituri)")
        lines.append("")

        # CD metadata
        lines.append("CD metadata:")
        lines.append("  Release: %s - %s" % (
                     ripResult.artist, ripResult.title))
        lines.append("  CDDB Disc ID: %s" % ripResult. table.getCDDBDiscId())
        lines.append("  MusicBrainz Disc ID: %s" %
                     ripResult. table.getMusicBrainzDiscId())
        lines.append("  MusicBrainz lookup url: %s" %
                     ripResult. table.getMusicBrainzSubmitURL())
        lines.append("")

        # TOC section
        lines.append("TOC:")
        table = ripResult.table

        # Test for HTOA presence
        htoa = None
        try:
            htoa = table.tracks[0].getIndex(0)
        except KeyError:
            pass

        # If True, include HTOA line into log's TOC
        if htoa and htoa.path:
            htoastart = htoa.absolute
            htoaend = table.getTrackEnd(0)
            htoalength = table.tracks[0].getIndex(1).absolute - htoastart
            lines.append("  0:")
            lines.append("    Start: %s" % common.framesToMSF(htoastart))
            lines.append("    Length: %s" % common.framesToMSF(htoalength))
            lines.append("    Start sector: %d" % htoastart)
            lines.append("    End sector: %d" % htoaend)
            lines.append("")

        # For every track include information in the TOC
        for t in table.tracks:
            start = t.getIndex(1).absolute
            length = table.getTrackLength(t.number)
            end = table.getTrackEnd(t.number)
            lines.append("  %d:" % t.number)
            lines.append("    Start: %s" % common.framesToMSF(start))
            lines.append("    Length: %s" % common.framesToMSF(length))
            lines.append("    Start sector: %d" % start)
            lines.append("    End sector: %d" % end)
            lines.append("")

        # Tracks section
        lines.append("Tracks:")
        duration = 0.0
        for t in ripResult.tracks:
            if not t.filename:
                continue
            lines.extend(self.trackLog(t))
            lines.append("")
            duration += t.testduration + t.copyduration

        # Status report
        lines.append("Conclusive status report:")
        arHeading = "  AccurateRip summary:"
        if self._inARDatabase == 0:
            lines.append("%s None of the tracks are present in the "
                         "AccurateRip database" % arHeading)
        else:
            nonHTOA = len(ripResult.tracks)
            if ripResult.tracks[0].number == 0:
                nonHTOA -= 1
            if self._accuratelyRipped == 0:
                lines.append("%s No tracks could be verified as accurate "
                             "(you may have a different pressing from the "
                             "one(s) in the database)" % arHeading)
            elif self._accuratelyRipped < nonHTOA:
                accurateTracks = nonHTOA - self._accuratelyRipped
                lines.append("%s Some tracks could not be verified as "
                             "accurate (%d/%d got no match)" % (
                                 arHeading, accurateTracks, nonHTOA))
            else:
                lines.append("%s All tracks accurately ripped" % arHeading)

        hsHeading = "  Health status:"
        if self._errors:
            lines.append("%s There were errors" % hsHeading)
        else:
            lines.append("%s No errors occurred" % hsHeading)
        lines.append("  EOF: End of status report")
        lines.append("")

        # Log hash
        hasher = hashlib.sha256()
        hasher.update("\n".join(lines).encode("utf-8"))
        lines.append("SHA-256 hash: %s" % hasher.hexdigest().upper())
        lines.append("")
        return lines

    def trackLog(self, trackResult):
        """Returns Tracks section lines: data picked from trackResult"""

        lines = []

        # Track number
        lines.append("  %d:" % trackResult.number)

        # Filename (including path) of ripped track
        lines.append("    Filename: %s" % trackResult.filename)

        # Pre-gap length
        pregap = trackResult.pregap
        if pregap:
            lines.append("    Pre-gap length: %s" % common.framesToMSF(pregap))

        # Peak level
        peak = trackResult.peak
        lines.append("    Peak level: %.6f" % peak)

        # Pre-emphasis status (only implemented in whipper)
        lines.append("    Pre-emphasis: Unknown (unsupported in morituri)")

        # Extraction speed
        if trackResult.copyspeed:
            lines.append("    Extraction speed: %.1f X" % (
                trackResult.copyspeed))

        # Extraction quality
        if trackResult.quality and trackResult.quality > 0.001:
            lines.append("    Extraction quality: %.2f %%" %
                         (trackResult.quality * 100.0, ))

        # Ripper Test CRC
        if trackResult.testcrc is not None:
            lines.append("    Test CRC: %08X" % trackResult.testcrc)

        # Ripper Copy CRC
        if trackResult.copycrc is not None:
            lines.append("    Copy CRC: %08X" % trackResult.copycrc)

        # AccurateRip track status
        # There's no support for AccurateRip v2 in morituri
        # AccurateRip v2 is supported in whipper
        if trackResult.accurip:
            lines.append("    AccurateRip v1:")
            self._inARDatabase += 1
            if trackResult.ARCRC == trackResult.ARDBCRC:
                lines.append("      Result: Found, exact match")
                self._accuratelyRipped += 1
            else:
                lines.append("      Result: Found, NO exact match")
            lines.append("      Confidence: %d" %
                         trackResult.ARDBConfidence)
            lines.append("      Local CRC: %08X" % trackResult.ARCRC)
            lines.append("      Remote CRC: %08X" % trackResult.ARDBCRC)
            lines.append("    AccurateRip v2:")
            lines.append("      Result: Unknown (unsupported in morituri)")
        elif trackResult.number != 0:
            lines.append("    AccurateRip v1:")
            lines.append("      Result: Track not present in "
                         "AccurateRip database")
            lines.append("    AccurateRip v2:")
            lines.append("      Result: Unknown (unsupported in morituri)")

        # Check if Test & Copy CRCs are equal
        if trackResult.testcrc == trackResult.copycrc:
            lines.append("    Status: Copy OK")
        else:
            self._errors = True
            lines.append("    Status: Error, CRC mismatch")
        return lines
