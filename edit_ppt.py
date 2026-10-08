from pptx import Presentation

def modify_presentation():
    prs = Presentation("presentation.pptx")

    # Claude will insert modifications here

    prs.save("presentation.pptx")

if __name__ == "__main__":
    modify_presentation()
