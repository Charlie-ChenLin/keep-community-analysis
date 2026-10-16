-- Optional macOS native PowerPoint rendering. Only opens/closes this deck.
-- Usage: osascript code/export_slides.applescript /absolute/deck.pptx /absolute/deck.pdf
on run groupArgs
    set groupPptPath to item 1 of groupArgs
    set groupPptFile to POSIX file groupPptPath
    set groupPptName to name of (info for groupPptFile)
    set groupPdfPath to (POSIX file (item 2 of groupArgs)) as text
    with timeout of 60 seconds
        tell application "Microsoft PowerPoint"
            activate
            open groupPptFile
            set groupDeck to presentation groupPptName
            save groupDeck in groupPdfPath as save as PDF
            close groupDeck saving no
        end tell
    end timeout
end run
