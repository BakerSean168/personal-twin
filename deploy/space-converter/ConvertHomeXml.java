import com.eteks.sweethome3d.io.HomeFileRecorder;
import com.eteks.sweethome3d.model.Home;

public final class ConvertHomeXml {
  public static void main(String[] args) throws Exception {
    if (args.length != 2) {
      throw new IllegalArgumentException("usage: ConvertHomeXml <input> <output>");
    }

    // preferXmlEntry=true is required for SweetHome3DJS files, which may
    // contain only Home.xml and no legacy serialized Home entry.
    HomeFileRecorder xmlAwareRecorder =
        new HomeFileRecorder(5, false, null, false, true);

    Home home = xmlAwareRecorder.readHome(args[0]);
    xmlAwareRecorder.writeHome(home, args[1]);

    System.out.println("converted " + args[0] + " -> " + args[1]);
  }
}
